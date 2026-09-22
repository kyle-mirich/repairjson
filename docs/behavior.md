# Repair rules and boundaries

`repairjson` returns one compact JSON value. Valid JSON within the nesting limit preserves its decoded value; whitespace and number spelling can change. Repair operates on text and never evaluates code.

## Locating a value

An initial UTF-8 BOM is removed. An opening Markdown fence at the start is skipped through its first newline; a closing fence at the end is removed. For example, `` ```json\n{a:1}\n``` `` becomes `{"a":1}`. Opening fences must have their content on a later line.

The lexer searches for the first `{` or `[` outside quoted text. This permits `Here is the JSON: {a:1}` and avoids braces in quoted preambles. It is a heuristic, not a Markdown or natural-language parser: brackets in prose can be mistaken for a payload, and unmatched quotes can hide a later payload.

If no container is found, a scalar is read. Empty input or input with no recognized value becomes `null`. Trailing prose and subsequent JSON values are ignored. Split JSON Lines into records before calling this library.

## Strings and literals

- Single and double quotes delimit strings; output always uses double quotes.
- Missing end quotes are inserted at end of input. A truncated string may absorb apparent punctuation through the end of the response.
- Standard JSON escapes are retained. Unknown escapes lose the backslash: `"a\qb"` becomes `"aqb"`.
- A partial Unicode escape is padded on the right with zeroes: `"\u12"` becomes `"\u1200"`. This is syntactic recovery, not a guess at the intended character.
- A trailing backslash is preserved as a literal backslash.
- Raw U+0000–U+001F characters are escaped without deleting them; CRLF remains two characters.
- `True`/`False` become `true`/`false`; `None`, `none`, and `Null` become `null`.
- Bare tokens, including Unicode tokens, become strings unless recognized as numbers or literals. Whitespace and JSON punctuation end bare tokens. Multiword bare strings, comments, and JavaScript expressions are not supported.
- `NaN` and `Infinity` become strings. A syntactically valid but extremely large exponent can still decode to infinity in Python; validate numeric ranges separately.

## Numbers

Normalization is textual and does not round through a floating-point type. Leading `+` signs and redundant integer zeroes are removed, `.5` becomes `0.5`, `1.` becomes `1.0`, and missing exponent digits become zero (`1e-` → `1e-0`). A lone sign becomes `0`; a lone decimal point becomes `0.0`. Ambiguous forms such as `1..2` or `1e2e3` become strings.

`repair` preserves arbitrarily long integer text. `loads` uses Python's integer and floating-point conversions, including the interpreter's integer digit limit.

## Containers

Missing commas and colons are inserted. Extra commas are skipped. Object keys without a value before a comma, closing delimiter, or end of input receive `null`. A bare key followed by another token can instead be interpreted as a missing colon: `{a 1}` → `{"a":1}`.

Closing delimiters belong to the nearest matching parent. A mismatched delimiter implicitly closes the current container, allowing the parent to consume it. For example:

```python
import repairjson

assert repairjson.loads("[{a: [1, 2}, {b: 3}]") == [{"a": [1, 2]}, {"b": 3}]
assert repairjson.loads("{a:, b: 2}") == {"a": None, "b": 2}
```

This can end a root value earlier than intended. For `[{a:1],2]`, the first `]` closes the root array, producing `[{"a":1}]`; `,2]` is trailing text and is ignored.

Duplicate keys are emitted in order. As with `json.loads`, `loads` retains the last value for a duplicate key.

## Resource limits and exceptions

Up to `MAX_DEPTH` (128) simultaneously nested containers are accepted. An additional opening container raises `ValueError` before recursing; partial output is not returned. This bound protects the native call stack. Input size remains the caller's responsibility.

The extension requires a Python Unicode string encodable as UTF-8. Non-string values raise `TypeError`; raw lone surrogates raise `UnicodeError`. Standard JSON escape text can represent surrogate code points, and `loads` follows Python's decoder behavior for them. Python allocation and numeric-conversion errors propagate normally.
