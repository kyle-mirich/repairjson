"""A local structured-output recovery example; no model calls or credentials."""

import json

import repairjson

MAX_INPUT_BYTES = 16 * 1024


def read_response(source: str) -> dict:
    """Try strict JSON first, then repair, and validate the application contract."""
    if len(source.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Response exceeds the application's 16 KiB input limit")
    try:
        value = json.loads(source)
    except json.JSONDecodeError:
        value = repairjson.loads(source)
    if not isinstance(value, dict) or set(value) != {"answer", "confidence"}:
        raise ValueError("Expected exactly answer and confidence fields")
    if not isinstance(value["answer"], str) or not value["answer"].strip():
        raise ValueError("Expected a nonempty answer string")
    confidence = value["confidence"]
    # bool is a subclass of int, so a plain isinstance check would accept True.
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        raise ValueError("Expected finite numeric confidence between 0 and 1")
    return value


def main() -> None:
    examples = [
        ("valid JSON", '{"answer":"42","confidence":0.9}'),
        ("malformed response", "Here is the result: ```json\n{answer: '42', confidence: .9,}"),
        ("truncated response", '{"answer":"partial","confidence":'),
        ("incorrect type", "{answer: '42', confidence: True}"),
    ]
    for label, source in examples:
        try:
            print(f"{label}: {read_response(source)!r}")
        except (ValueError, UnicodeError) as error:
            print(f"{label}: rejected ({error})")


if __name__ == "__main__":
    main()
