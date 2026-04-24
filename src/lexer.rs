pub struct Lexer<'a> {
    bytes: &'a [u8],
    pos: usize,
    end: usize,
}

impl<'a> Lexer<'a> {
    pub fn new(input: &'a str) -> Self {
        let bytes = input.as_bytes();
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

    pub fn skip_whitespace(&mut self) {
        while let Some(byte) = self.peek() {
            if !byte.is_ascii_whitespace() {
                break;
            }
            self.pos += 1;
        }
    }

    pub fn prefer_structural_value_start(&mut self) {
        self.skip_whitespace();

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

    pub fn peek_non_whitespace(&self) -> Option<u8> {
        let mut cursor = self.pos;
        while cursor < self.end {
            let byte = self.bytes[cursor];
            if !byte.is_ascii_whitespace() {
                return Some(byte);
            }
            cursor += 1;
        }
        None
    }

    pub fn read_bare_token(&mut self) -> &'a [u8] {
        let start = self.pos;
        while let Some(byte) = self.peek() {
            if byte.is_ascii_whitespace() || matches!(byte, b',' | b'[' | b']' | b'{' | b'}' | b':')
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
