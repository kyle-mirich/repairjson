use crate::lexer::Lexer;

/// Maximum number of simultaneously open objects and arrays.
pub const MAX_DEPTH: usize = 128;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DepthLimitExceeded;

impl std::fmt::Display for DepthLimitExceeded {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "JSON nesting exceeds the limit of {MAX_DEPTH} containers"
        )
    }
}

impl std::error::Error for DepthLimitExceeded {}

pub fn repair(input: &str) -> Result<String, DepthLimitExceeded> {
    Parser::new(input).repair()
}

struct Parser<'a> {
    lexer: Lexer<'a>,
    output: Vec<u8>,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            lexer: Lexer::new(input),
            output: Vec::with_capacity(input.len().saturating_add(16)),
        }
    }

    fn repair(mut self) -> Result<String, DepthLimitExceeded> {
        self.lexer.prefer_structural_value_start();

        if !self.parse_value(0)? {
            self.output.extend_from_slice(b"null");
        }

        // Input is UTF-8; only ASCII syntax is removed or inserted. Non-ASCII
        // bytes are always copied together as part of a token or string.
        Ok(String::from_utf8(self.output).expect("repair output is always utf-8"))
    }

    fn parse_value(&mut self, depth: usize) -> Result<bool, DepthLimitExceeded> {
        self.skip_to_value_start();

        let Some(byte) = self.lexer.peek() else {
            return Ok(false);
        };

        match byte {
            b'{' | b'[' => {
                if depth >= MAX_DEPTH {
                    return Err(DepthLimitExceeded);
                }
                if byte == b'{' {
                    self.parse_object(depth + 1)?;
                } else {
                    self.parse_array(depth + 1)?;
                }
                Ok(true)
            }
            b'"' | b'\'' => Ok(self.parse_string()),
            b'+' | b'-' | b'.' | b'0'..=b'9' => Ok(self.parse_number_or_word()),
            _ if is_identifier_start(byte) => Ok(self.parse_identifier_value()),
            // Separators and closing delimiters belong to the caller. In
            // particular, a missing object value must not eat the next key.
            _ => Ok(false),
        }
    }

    fn parse_object(&mut self, depth: usize) -> Result<(), DepthLimitExceeded> {
        self.lexer.bump();
        self.output.push(b'{');
        let mut has_entries = false;

        loop {
            self.lexer.skip_whitespace();
            if self.lexer.consume_if(b'}') || self.lexer.is_eof() {
                break;
            }
            // Close this object implicitly and let the parent consume ']'.
            if self.lexer.peek() == Some(b']') {
                break;
            }
            if !self.can_start_object_key() {
                self.lexer.bump();
                continue;
            }

            if has_entries {
                self.output.push(b',');
            }
            self.parse_key();
            self.lexer.skip_whitespace();
            self.lexer.consume_if(b':');
            self.output.push(b':');
            if !self.parse_value(depth)? {
                self.output.extend_from_slice(b"null");
            }
            has_entries = true;
        }

        self.output.push(b'}');
        Ok(())
    }

    fn parse_array(&mut self, depth: usize) -> Result<(), DepthLimitExceeded> {
        self.lexer.bump();
        self.output.push(b'[');
        let mut has_items = false;

        loop {
            self.lexer.skip_whitespace();
            if self.lexer.consume_if(b']') || self.lexer.is_eof() {
                break;
            }
            // A parent's closing brace must not become part of this array.
            if self.lexer.peek() == Some(b'}') {
                break;
            }
            if !self.lexer.peek().is_some_and(is_value_start) {
                self.lexer.bump();
                continue;
            }

            if has_items {
                self.output.push(b',');
            }
            self.parse_value(depth)?;
            has_items = true;
        }

        self.output.push(b']');
        Ok(())
    }

    // Called only after can_start_object_key has recognized a nonempty key.
    fn parse_key(&mut self) {
        if matches!(self.lexer.peek(), Some(b'"' | b'\'')) {
            self.parse_string();
        } else {
            let token = self.lexer.read_bare_token();
            push_quoted_bytes(&mut self.output, token);
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

            if byte == b'\\' {
                self.push_escaped_char();
            } else {
                push_string_byte(&mut self.output, byte);
            }
        }

        self.output.push(b'"');
        true
    }

    fn push_escaped_char(&mut self) {
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
                    if let Some(hex) = self.lexer.peek()
                        && hex.is_ascii_hexdigit()
                    {
                        self.output.push(hex);
                        self.lexer.bump();
                        continue;
                    }
                    self.output.extend_from_slice(b"0");
                }
            }
            // Unknown escapes lose the backslash but preserve the character.
            _ => push_string_byte(&mut self.output, next),
        }
    }

    fn parse_number_or_word(&mut self) -> bool {
        let token = self.lexer.read_bare_token();
        if token.is_empty() {
            return false;
        }

        if push_number(&mut self.output, token) {
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
            if is_value_start(byte) || matches!(byte, b',' | b']' | b'}') {
                break;
            }
            self.lexer.bump();
            self.lexer.skip_whitespace();
        }
    }

    fn can_start_object_key(&self) -> bool {
        match self.lexer.peek() {
            Some(b'"' | b'\'' | b'-' | b'0'..=b'9') => true,
            Some(byte) => is_identifier_start(byte),
            None => false,
        }
    }
}

fn is_identifier_start(byte: u8) -> bool {
    byte.is_ascii_alphabetic() || byte >= 0x80 || matches!(byte, b'_' | b'$')
}

fn is_value_start(byte: u8) -> bool {
    matches!(
        byte,
        b'{' | b'[' | b'"' | b'\'' | b'+' | b'-' | b'.' | b'0'..=b'9'
    ) || is_identifier_start(byte)
}

// The same escaping rules apply to quoted input and repaired bare tokens.
fn push_string_byte(output: &mut Vec<u8>, byte: u8) {
    match byte {
        b'"' => output.extend_from_slice(br#"\""#),
        b'\\' => output.extend_from_slice(br#"\\"#),
        b'\n' => output.extend_from_slice(br#"\n"#),
        b'\r' => output.extend_from_slice(br#"\r"#),
        b'\t' => output.extend_from_slice(br#"\t"#),
        0x00..=0x1f => {
            const HEX: &[u8; 16] = b"0123456789abcdef";
            output.extend_from_slice(br#"\u00"#);
            output.push(HEX[(byte >> 4) as usize]);
            output.push(HEX[(byte & 0xf) as usize]);
        }
        _ => output.push(byte),
    }
}

fn push_quoted_bytes(output: &mut Vec<u8>, bytes: &[u8]) {
    output.push(b'"');
    for &byte in bytes {
        push_string_byte(output, byte);
    }
    output.push(b'"');
}

// Validate before writing so ambiguous tokens can be quoted without rollback.
// Normalize directly into the output buffer, without allocating per number.
fn push_number(output: &mut Vec<u8>, token: &[u8]) -> bool {
    let (negative, normalized) = match token.first() {
        Some(b'-') => (true, &token[1..]),
        Some(b'+') => (false, &token[1..]),
        _ => (false, token),
    };
    if normalized.is_empty() {
        output.push(b'0');
        return true;
    }

    let exponent_index = normalized.iter().position(|b| matches!(b, b'e' | b'E'));
    let (mantissa, exponent) = match exponent_index {
        Some(i) => (&normalized[..i], Some(&normalized[i + 1..])),
        None => (normalized, None),
    };
    if mantissa.is_empty()
        || !mantissa.iter().all(|b| b.is_ascii_digit() || *b == b'.')
        || mantissa.iter().filter(|&&b| b == b'.').count() > 1
    {
        return false;
    }
    if let Some(exponent) = exponent {
        let digits = match exponent.first() {
            Some(b'+' | b'-') => &exponent[1..],
            _ => exponent,
        };
        if !digits.iter().all(u8::is_ascii_digit) {
            return false;
        }
    }

    if negative {
        output.push(b'-');
    }
    let dot = mantissa.iter().position(|&b| b == b'.');
    let integer = dot.map_or(mantissa, |i| &mantissa[..i]);
    let first_nonzero = integer.iter().position(|&b| b != b'0');
    match first_nonzero {
        Some(i) => output.extend_from_slice(&integer[i..]),
        None => output.push(b'0'),
    }
    if let Some(dot) = dot {
        output.push(b'.');
        let fraction = &mantissa[dot + 1..];
        output.extend_from_slice(fraction);
        if fraction.is_empty() {
            output.push(b'0');
        }
    }
    if let Some(exponent) = exponent {
        output.push(b'e');
        output.extend_from_slice(exponent);
        if exponent.is_empty() || matches!(exponent.last(), Some(b'+' | b'-')) {
            output.push(b'0');
        }
    }
    true
}

#[cfg(test)]
mod tests {
    fn repair(input: &str) -> String {
        super::repair(input).unwrap()
    }

    #[test]
    fn bounds_nesting_without_truncating_input() {
        let allowed = "[".repeat(super::MAX_DEPTH);
        assert!(super::repair(&allowed).is_ok());
        assert_eq!(
            super::repair(&(allowed + "[")),
            Err(super::DepthLimitExceeded)
        );
    }

    #[test]
    fn preserves_missing_values_and_container_boundaries() {
        assert_eq!(repair("{a:,b:2}"), r#"{"a":null,"b":2}"#);
        assert_eq!(repair("[{a:1],2]"), r#"[{"a":1}]"#);
        assert_eq!(repair("[{a:1}, {b:}]"), r#"[{"a":1},{"b":null}]"#);
        assert_eq!(repair("{a 1,b 2}"), r#"{"a":1,"b":2}"#);
    }

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
        assert_eq!(repair("'tab\\\tvalue'"), "\"tab\\tvalue\"");
    }

    #[test]
    fn repairs_nested_values_without_commas() {
        assert_eq!(repair("[1{a:2}]"), "[1,{\"a\":2}]");
        assert_eq!(repair("{a:1{b:2}}"), "{\"a\":1,\"b\":2}");
    }

    #[test]
    fn repairs_malformed_number_prefixes_and_exponents() {
        assert_eq!(repair("{'a': .5}"), "{\"a\":0.5}");
        assert_eq!(repair("{'a': +.5}"), "{\"a\":0.5}");
        assert_eq!(repair("{'a': -.5}"), "{\"a\":-0.5}");
        assert_eq!(repair("{'a': +5}"), "{\"a\":5}");
        assert_eq!(repair("{'a': -5}"), "{\"a\":-5}");
        assert_eq!(repair("{'a': -1.25}"), "{\"a\":-1.25}");
        assert_eq!(repair("{'a': -1e3}"), "{\"a\":-1e3}");
        assert_eq!(repair("{'a': 1e}"), "{\"a\":1e0}");
        assert_eq!(repair("{'a': 1e+}"), "{\"a\":1e+0}");
        assert_eq!(repair("{'a': .e}"), "{\"a\":0.0e0}");
        assert_eq!(repair("{'a': 1.e2}"), "{\"a\":1.0e2}");
        assert_eq!(repair("{'a': 01}"), "{\"a\":1}");
        assert_eq!(repair("{'a': 00.5}"), "{\"a\":0.5}");
        assert_eq!(repair("{'a': 1..2}"), "{\"a\":\"1..2\"}");
    }

    #[test]
    fn prefers_structural_json_after_chatty_preamble() {
        assert_eq!(repair("result = {a:1}"), "{\"a\":1}");
        assert_eq!(
            repair("Here is the JSON:\n```json\n{a:1}\n```"),
            "{\"a\":1}"
        );
        assert_eq!(repair("### JSON\n{a:1}"), "{\"a\":1}");
        assert_eq!(repair("- JSON follows\n{a:1}"), "{\"a\":1}");
        assert_eq!(repair("1. JSON follows\n[1,2]"), "[1,2]");
        assert_eq!(repair("Items follow: [1,2,3]"), "[1,2,3]");
        assert_eq!(repair("I'm sorry, here is JSON: {a:1}"), "{\"a\":1}");
        assert_eq!(repair("Note: 'quoted preamble' {a:1}"), "{\"a\":1}");
        assert_eq!(repair("Note: '{not the payload}' {a:1}"), "{\"a\":1}");
    }
}
