#[derive(Clone)]
pub struct Lexer<'a> {
    bytes: &'a [u8],
    pos: usize,
    end: usize,
}

impl<'a> Lexer<'a> {
    pub fn new(input: &'a str) -> Self {
        let bytes = input.strip_prefix('\u{feff}').unwrap_or(input).as_bytes();
        let (pos, end) = trim_markdown_fences(bytes);
        Self { bytes, pos, end }
    }

    pub fn is_eof(&self) -> bool {
        self.pos >= self.end
    }

    pub fn peek(&self) -> Option<u8> {
        self.bytes
            .get(self.pos)
            .copied()
            .filter(|_| self.pos < self.end)
    }

    pub fn next(&mut self) -> Option<u8> {
        let byte = self.peek()?;
        self.pos += 1;
        Some(byte)
    }

    pub fn bump(&mut self) -> bool {
        self.next().is_some()
    }

    pub fn skip_trivia(&mut self) {
        while let Some(byte) = self.peek() {
            if byte.is_ascii_whitespace() {
                self.pos += 1;
            } else if let Some(end) = comment_end(self.bytes, self.pos, self.end) {
                self.pos = end;
            } else {
                return;
            }
        }
    }

    // Check a possible missing-comma key without moving the real cursor.
    pub fn bare_key_follows(&self) -> bool {
        let mut lookahead = self.clone();
        lookahead.skip_trivia();
        !lookahead.read_bare_token().is_empty() && {
            lookahead.skip_trivia();
            lookahead.peek() == Some(b':')
        }
    }

    pub fn next_significant_byte(&self) -> Option<u8> {
        let mut lookahead = self.clone();
        lookahead.skip_trivia();
        lookahead.peek()
    }

    pub fn prefer_structural_value_start(&mut self) {
        self.skip_trivia();

        if self.peek().is_none() {
            return;
        }

        let mut cursor = self.pos;
        let mut quote = None;
        while cursor < self.end {
            let byte = self.bytes[cursor];

            if let Some(active_quote) = quote {
                if byte == b'\\' {
                    cursor = (cursor + 2).min(self.end);
                    continue;
                }

                if byte == active_quote {
                    quote = None;
                }

                cursor += 1;
                continue;
            }

            if matches!(byte, b'"' | b'\'') {
                if byte == b'\'' && self.is_word_apostrophe(cursor) {
                    cursor += 1;
                    continue;
                }

                quote = Some(byte);
                cursor += 1;
                continue;
            }

            if let Some(end) = comment_end(self.bytes, cursor, self.end) {
                cursor = end;
                continue;
            }

            if matches!(byte, b'{' | b'[') {
                self.pos = cursor;
                return;
            }
            cursor += 1;
        }
    }

    pub fn consume_if(&mut self, expected: u8) -> bool {
        if self.peek() == Some(expected) {
            self.pos += 1;
            return true;
        }

        false
    }

    pub fn read_bare_token(&mut self) -> &'a [u8] {
        let start = self.pos;
        while let Some(byte) = self.peek() {
            if byte.is_ascii_whitespace()
                || matches!(byte, b',' | b'[' | b']' | b'{' | b'}' | b':' | b'"' | b'\'')
                || starts_comment(self.bytes, self.pos, self.end)
            {
                break;
            }
            self.pos += 1;
        }
        &self.bytes[start..self.pos]
    }

    fn is_word_apostrophe(&self, cursor: usize) -> bool {
        cursor > self.pos
            && cursor + 1 < self.end
            && self.bytes[cursor - 1].is_ascii_alphanumeric()
            && self.bytes[cursor + 1].is_ascii_alphanumeric()
    }
}

fn starts_comment(bytes: &[u8], pos: usize, end: usize) -> bool {
    pos + 1 < end && bytes[pos] == b'/' && matches!(bytes[pos + 1], b'/' | b'*')
}

// Comments are recognized only outside strings. An unfinished comment extends
// to EOF, so the parser can close any containers opened before it.
fn comment_end(bytes: &[u8], pos: usize, end: usize) -> Option<usize> {
    if !starts_comment(bytes, pos, end) {
        return None;
    }
    let mut cursor = pos + 2;
    if bytes[pos + 1] == b'/' {
        while cursor < end && !matches!(bytes[cursor], b'\r' | b'\n') {
            cursor += 1;
        }
    } else {
        while cursor + 1 < end {
            if bytes[cursor] == b'*' && bytes[cursor + 1] == b'/' {
                return Some(cursor + 2);
            }
            cursor += 1;
        }
        cursor = end;
    }
    Some(cursor)
}

fn trim_markdown_fences(bytes: &[u8]) -> (usize, usize) {
    let mut start = 0;
    let mut end = bytes.len();

    while start < end && bytes[start].is_ascii_whitespace() {
        start += 1;
    }

    if bytes[start..end].starts_with(b"```") {
        start += 3;
        while start < end && !matches!(bytes[start], b'\n' | b'\r') {
            start += 1;
        }
        while start < end && matches!(bytes[start], b'\n' | b'\r') {
            start += 1;
        }
    }

    while end > start && bytes[end - 1].is_ascii_whitespace() {
        end -= 1;
    }

    if end >= start + 3 && &bytes[end - 3..end] == b"```" {
        end -= 3;
        while end > start && bytes[end - 1].is_ascii_whitespace() {
            end -= 1;
        }
    }

    (start, end)
}
