"""Public behavior at parser boundaries, including historically lossy repairs."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import repairjson


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", None),
        (" \n\t", None),
        ("{}", {}),
        ("[]", []),
        ("{a:,b:2}", {"a": None, "b": 2}),
        ('{"a":}', {"a": None}),
        ('[{"a":}, {"b":2}]', [{"a": None}, {"b": 2}]),
        ('[{"a":1],2]', [{"a": 1}]),
        ('{"a":[1,2},"b":3}', {"a": [1, 2]}),
        ('[{"a":[1,2}, {"b":3}]', [{"a": [1, 2]}, {"b": 3}]),
        ("{a 1,b 2}", {"a": 1, "b": 2}),
        ('{"a" "value", "b" [1,2]}', {"a": "value", "b": [1, 2]}),
        ('[1"two",true"x"]', [1, "two", True, "x"]),
        (
            "{名字: 中文, café: résumé, emoji: 🙂}",
            {"名字": "中文", "café": "résumé", "emoji": "🙂"},
        ),
        ('\ufeff{"ok":true}', {"ok": True}),
        ("\ufeff```json\r\n{ok:True}\r\n```", {"ok": True}),
        ("[1,,2,,,]", [1, 2]),
        ("{a:1,,,b:2,}", {"a": 1, "b": 2}),
        ('{"key": "unfinished', {"key": "unfinished"}),
        ('"trailing\\', "trailing\\"),
        (r'"bad\qescape"', "badqescape"),
        (r'"\u12"', "\u1200"),
        (r'"\uZZZZ"', "\u0000ZZZZ"),
        (r'"\ud83d\ude42"', "🙂"),
        (r"'it\'s fine'", "it's fine"),
        ('"a\x00b\r\nc"', "a\x00b\r\nc"),
        ("[NaN, Infinity, -Infinity]", ["NaN", "Infinity", "-Infinity"]),
        ("1e9999", float("inf")),
        ('{"a":1,"a":2}', {"a": 2}),
        ("{a:1} trailing {b:2}", {"a": 1}),
    ],
)
def test_repairs_boundaries(source, expected):
    repaired = repairjson.repair(source)
    assert json.loads(repaired) == expected
    assert repairjson.loads(source) == expected
    assert repairjson.repair(repaired) == repaired


@pytest.mark.parametrize("control", range(32))
@pytest.mark.parametrize("escaped", [False, True])
def test_control_characters_are_preserved(control, escaped):
    char = chr(control)
    source = '"before' + ("\\" if escaped else "") + char + 'after"'
    assert repairjson.loads(source) == "before" + char + "after"


@pytest.mark.parametrize(
    "function",
    [repairjson.repair, repairjson.repair_json, repairjson.repair_to_string, repairjson.loads],
)
def test_nesting_limit_is_a_python_exception(function):
    assert repairjson.MAX_DEPTH == 128
    with pytest.raises(ValueError, match="nesting exceeds the limit of 128"):
        function("[" * 100_000)
    with pytest.raises(ValueError, match="nesting"):
        function('{"a":' * (repairjson.MAX_DEPTH + 1))
    # An exception must not leave shared parser state behind.
    assert function("[]") in ("[]", [])


def test_depth_boundary_is_supported():
    source = "[" * repairjson.MAX_DEPTH + "0" + "]" * repairjson.MAX_DEPTH
    assert repairjson.repair(source) == source
    value = repairjson.loads(source)
    for _ in range(repairjson.MAX_DEPTH):
        value = value[0]
    assert value == 0


@pytest.mark.parametrize("value", [None, 42, b"{}", {}, []])
def test_requires_a_unicode_string(value):
    with pytest.raises(TypeError):
        repairjson.repair(value)


def test_raw_surrogate_input_is_rejected():
    with pytest.raises(UnicodeError):
        repairjson.repair('"\ud800"')


def test_concurrent_repairs_have_no_shared_state():
    sources = ["{index: " + str(i) + ", values: [True, None,]}" for i in range(256)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(repairjson.loads, sources))
    assert results == [{"index": i, "values": [True, None]} for i in range(256)]


def test_type_information_is_installed():
    package = Path(repairjson.__file__).parent
    assert package.joinpath("py.typed").is_file()
    assert package.joinpath("repairjson.pyi").is_file()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('{"command":"printf ok" // keep this\\n}', {"command": "printf ok"}),
        ('{/*a*/"command":"printf ok"}', {"command": "printf ok"}),
        ("{a:1/* note */,b:2 // line\n,c:3}", {"a": 1, "b": 2, "c": 3}),
        ("[1/* note */, // line\r\n2]", [1, 2]),
        ("/* [ignore me] */ Here: {a:1}", {"a": 1}),
        ("Here: /* [ignore me] */ {a:1}", {"a": 1}),
        ("// [ignore me]\n{a:1}", {"a": 1}),
        ("{/* unfinished", {}),
        ("[1, /* unfinished", [1]),
        ("/* only a comment */", None),
        (
            '{url:"https://example.com",text:"/*literal*/ //literal"}',
            {"url": "https://example.com", "text": "/*literal*/ //literal"},
        ),
        ('{a:"value" next:2}', {"a": "value", "next": 2}),
        ('{a:"value"next:2}', {"a": "value", "next": 2}),
        ('{a:"value"/*note*/名字:2}', {"a": "value", "名字": 2}),
        ('{a:"value" // note\n next:2}', {"a": "value", "next": 2}),
    ],
)
def test_comments_and_string_boundaries(source, expected):
    assert repairjson.loads(source) == expected


@pytest.mark.parametrize(
    "function",
    [repairjson.repair, repairjson.loads, repairjson.repair_json, repairjson.repair_to_string],
)
@pytest.mark.parametrize(
    "source",
    [
        '{"command": "say "hello" now"}',
        '{"command": "say "你好" now"}',
        '{"command": "say "42" now"}',
    ],
)
def test_rejects_ambiguous_inner_quotes(function, source):
    with pytest.raises(ValueError, match="Ambiguous unescaped quote in object value"):
        function(source)


def test_escaped_inner_quotes_are_preserved():
    assert repairjson.loads(r'{"command": "say \"hello\" now"}') == {"command": 'say "hello" now'}
