use smallvec::SmallVec;

use crate::lexer::Lexer;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Context {
    Object,
    Array,
}

pub fn repair(input: &str) -> String {
    Parser::new(input).repair()
}

struct Parser<'a> {
    lexer: Lexer<'a>,
    output: Vec<u8>,
    stack: SmallVec<[Context; 8]>,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            lexer: Lexer::new(input),
            output: Vec::with_capacity(input.len().saturating_add(16)),
            stack: SmallVec::new(),
        }
    }

    fn repair(mut self) -> String {
        if !self.parse_value() {
            self.output.extend_from_slice(b"null");
        }

        String::from_utf8(self.output).expect("repair output is always utf-8")
    }

    fn parse_value(&mut self) -> bool {
        self.skip_to_value_start();

        let Some(byte) = self.lexer.peek() else {
            return false;
        };

        match byte {
            b'{' => self.parse_object(),
            b'[' => self.parse_array(),
            b'"' | b'\'' => self.parse_string(),
            b'-' | b'0'..=b'9' => self.parse_number_or_word(),
            _ if is_identifier_start(byte) => self.parse_identifier_value(),
            _ => {
                self.lexer.bump();
                self.parse_value()
            }
        }
    }

    fn parse_object(&mut self) -> bool {
        self.lexer.consume_if(b'{');
        self.stack.push(Context::Object);
        self.output.push(b'{');

        let mut entry_count = 0;

        loop {
            self.lexer.skip_whitespace();

            if self.lexer.consume_if(b'}') {
                break;
            }

            if self.lexer.is_eof() {
                break;
            }

            if self.lexer.consume_if(b',') {
                continue;
            }

            if !self.can_start_object_key() {
                self.lexer.bump();
                continue;
            }

            if entry_count > 0 {
                self.output.push(b',');
            }

            if !self.parse_key() {
                self.output.pop();
                break;
            }

            self.lexer.skip_whitespace();

            if self.lexer.consume_if(b':') {
                self.output.push(b':');
            } else {
                self.output.extend_from_slice(b":null");
                entry_count += 1;
                continue;
            }

            self.lexer.skip_whitespace();
            if !self.parse_value() {
                self.output.extend_from_slice(b"null");
            }
            entry_count += 1;

            self.lexer.skip_whitespace();
            if self.lexer.consume_if(b',') {
                if self.lexer.peek_non_whitespace() == Some(b'}') {
                    continue;
                }
            }
        }

        self.output.push(b'}');
        self.stack.pop();
        true
    }

    fn parse_array(&mut self) -> bool {
        self.lexer.consume_if(b'[');
        self.stack.push(Context::Array);
        self.output.push(b'[');

        let mut item_count = 0;

        loop {
            self.lexer.skip_whitespace();

            if self.lexer.consume_if(b']') {
                break;
            }

            if self.lexer.is_eof() {
                break;
            }

            if self.lexer.consume_if(b',') {
                continue;
            }

            if !self.can_start_value() {
                self.lexer.bump();
                continue;
            }

            if item_count > 0 {
                self.output.push(b',');
            }

            if !self.parse_value() {
                self.output.pop();
                break;
            }
            item_count += 1;

            self.lexer.skip_whitespace();
            if self.lexer.consume_if(b',') {
                if self.lexer.peek_non_whitespace() == Some(b']') {
                    continue;
                }
            }
        }

        self.output.push(b']');
        self.stack.pop();
        true
    }

    fn parse_key(&mut self) -> bool {
        self.lexer.skip_whitespace();

        match self.lexer.peek() {
            Some(b'"' | b'\'') => self.parse_string(),
            Some(byte) if is_identifier_start(byte) || byte.is_ascii_digit() || byte == b'-' => {
                let token = self.lexer.read_bare_token();
                if token.is_empty() {
                    return false;
                }
                push_quoted_bytes(&mut self.output, token);
                true
            }
            _ => false,
        }
    }

    fn parse_string(&mut self) -> bool {
        let Some(quote) = self.lexer.next() else {
            return false;
        };

        self.output.push(b'"');

        while let Some(byte) = self.lexer.next() {
            if byte == quote {
                self.output.push(b'"');
                return true;
            }

            match byte {
                b'\\' => self.push_escaped_char(quote),
                b'"' => self.output.extend_from_slice(br#"\""#),
                b'\n' => self.output.extend_from_slice(br#"\n"#),
                b'\r' => {
                    if self.lexer.peek() == Some(b'\n') {
                        self.lexer.bump();
                    }
                    self.output.extend_from_slice(br#"\n"#);
                }
                b'\t' => self.output.extend_from_slice(br#"\t"#),
                0x00..=0x08 | 0x0B | 0x0C | 0x0E..=0x1F => {}
                _ => self.output.push(byte),
            }
        }

        self.output.push(b'"');
        true
    }

    fn push_escaped_char(&mut self, quote: u8) {
        let Some(next) = self.lexer.next() else {
            self.output.extend_from_slice(br#"\\"#);
            return;
        };

        match next {
            b'"' => self.output.extend_from_slice(br#"\""#),
            b'\\' => self.output.extend_from_slice(br#"\\"#),
            b'/' => self.output.extend_from_slice(br#"\/"#),
            b'b' | b'f' | b'n' | b'r' | b't' => {
                self.output.push(b'\\');
                self.output.push(next);
            }
            b'u' => {
                self.output.extend_from_slice(br#"\u"#);
                for _ in 0..4 {
                    if let Some(hex) = self.lexer.peek() {
                        if hex.is_ascii_hexdigit() {
                            self.output.push(hex);
                            self.lexer.bump();
                            continue;
                        }
                    }
                    self.output.extend_from_slice(b"0");
                }
            }
            b'\'' if quote == b'\'' => self.output.push(b'\''),
            b'\n' => self.output.extend_from_slice(br#"\n"#),
            b'\r' => {
                if self.lexer.peek() == Some(b'\n') {
                    self.lexer.bump();
                }
                self.output.extend_from_slice(br#"\n"#);
            }
            _ => self.output.push(next),
        }
    }

    fn parse_number_or_word(&mut self) -> bool {
        let token = self.lexer.read_bare_token();
        if token.is_empty() {
            return false;
        }

        if token
            .iter()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E'))
        {
            push_sanitized_number(&mut self.output, token);
            return true;
        }

        push_quoted_bytes(&mut self.output, token);
        true
    }

    fn parse_identifier_value(&mut self) -> bool {
        let token = self.lexer.read_bare_token();
        if token.is_empty() {
            return false;
        }

        match token {
            b"true" | b"True" => self.output.extend_from_slice(b"true"),
            b"false" | b"False" => self.output.extend_from_slice(b"false"),
            b"null" | b"Null" | b"None" | b"none" => self.output.extend_from_slice(b"null"),
            _ => push_quoted_bytes(&mut self.output, token),
        }

        true
    }

    fn skip_to_value_start(&mut self) {
        self.lexer.skip_whitespace();

        while let Some(byte) = self.lexer.peek() {
            if is_value_start(byte) {
                break;
            }

            if matches!(byte, b',' | b':' | b';') {
                self.lexer.bump();
                self.lexer.skip_whitespace();
                continue;
            }

            self.lexer.bump();
            self.lexer.skip_whitespace();
        }
    }

    fn can_start_object_key(&mut self) -> bool {
        self.lexer.skip_whitespace();
        match self.lexer.peek() {
            Some(b'"' | b'\'') | Some(b'-' | b'0'..=b'9') => true,
            Some(byte) => is_identifier_start(byte),
            None => false,
        }
    }

    fn can_start_value(&mut self) -> bool {
        self.lexer.skip_whitespace();
        self.lexer.peek().is_some_and(is_value_start)
    }
}

fn is_identifier_start(byte: u8) -> bool {
    byte.is_ascii_alphabetic() || matches!(byte, b'_' | b'$')
}

fn is_value_start(byte: u8) -> bool {
    matches!(byte, b'{' | b'[' | b'"' | b'\'' | b'-' | b'0'..=b'9') || is_identifier_start(byte)
}

fn push_quoted_bytes(output: &mut Vec<u8>, bytes: &[u8]) {
    output.push(b'"');
    for &byte in bytes {
        match byte {
            b'"' => output.extend_from_slice(br#"\""#),
            b'\\' => output.extend_from_slice(br#"\\"#),
            b'\n' => output.extend_from_slice(br#"\n"#),
            b'\r' => output.extend_from_slice(br#"\n"#),
            b'\t' => output.extend_from_slice(br#"\t"#),
            0x00..=0x08 | 0x0B | 0x0C | 0x0E..=0x1F => {}
            _ => output.push(byte),
        }
    }
    output.push(b'"');
}

fn push_sanitized_number(output: &mut Vec<u8>, token: &[u8]) {
    if token == b"-" || token == b"+" {
        output.extend_from_slice(b"0");
        return;
    }

    if token.starts_with(b".") {
        output.extend_from_slice(b"0");
    } else if token.starts_with(b"-.") {
        output.extend_from_slice(b"-0");
        output.extend_from_slice(&token[1..]);
        return;
    } else if token.starts_with(b"+.") {
        output.extend_from_slice(b"0");
        output.extend_from_slice(&token[1..]);
        return;
    }

    output.extend_from_slice(token);

    if token.ends_with(b".") {
        output.extend_from_slice(b"0");
    }
}

#[cfg(test)]
mod tests {
    use super::repair;

    #[test]
    fn repairs_target_cases() {
        assert_eq!(repair("{'a': 'b'}"), "{\"a\":\"b\"}");
        assert_eq!(
            repair("{'a': True, 'b': False, 'c': None}"),
            "{\"a\":true,\"b\":false,\"c\":null}"
        );
        assert_eq!(repair("{a: 1, b: 2}"), "{\"a\":1,\"b\":2}");
        assert_eq!(repair("{\"a\": 1,}"), "{\"a\":1}");
        assert_eq!(repair("{\"a\": 1 \"b\": 2}"), "{\"a\":1,\"b\":2}");
        assert_eq!(repair("{\"a\": [1, 2, 3}"), "{\"a\":[1,2,3]}");
        assert_eq!(repair("```json\n{\"a\": 1}\n```"), "{\"a\":1}");
    }

    #[test]
    fn escapes_literal_newlines_in_strings() {
        assert_eq!(
            repair("{\"a\": \"hello\nworld\"}"),
            "{\"a\":\"hello\\nworld\"}"
        );
    }
}
