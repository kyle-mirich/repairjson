import json

import repairjson


def test_repair_smoke():
    payload = '{"status": "ok"}'
    assert json.loads(repairjson.repair(payload)) == {"status": "ok"}


def test_repair_to_string_smoke():
    payload = '{"answer": 42}'
    assert json.loads(repairjson.repair_to_string(payload)) == {"answer": 42}


def test_repair_json_smoke():
    payload = '{"nested": {"value": true}}'
    assert json.loads(repairjson.repair_json(payload)) == {
        "nested": {"value": True}
    }


def test_repairs_target_cases():
    assert repairjson.repair("{'a': 'b'}") == '{"a":"b"}'
    assert (
        repairjson.repair("{'a': True, 'b': False, 'c': None}")
        == '{"a":true,"b":false,"c":null}'
    )
    assert repairjson.repair("{a: 1, b: 2}") == '{"a":1,"b":2}'
    assert repairjson.repair('{"a": 1,}') == '{"a":1}'
    assert repairjson.repair('{"a": 1 "b": 2}') == '{"a":1,"b":2}'
    assert repairjson.repair('{"a": [1, 2, 3}') == '{"a":[1,2,3]}'
    assert repairjson.repair('```json\n{"a": 1}\n```') == '{"a":1}'
    assert repairjson.repair('{"a": "hello\nworld"}') == '{"a":"hello\\nworld"}'


def test_repairs_nested_values_without_commas():
    assert repairjson.repair("[1{a:2}]") == '[1,{"a":2}]'
    assert repairjson.repair("{a:1{b:2}}") == '{"a":1,"b":2}'


def test_repairs_malformed_number_prefixes_and_exponents():
    assert repairjson.repair("{'a': .5}") == '{"a":0.5}'
    assert repairjson.repair("{'a': +.5}") == '{"a":0.5}'
    assert repairjson.repair("{'a': -.5}") == '{"a":-0.5}'
    assert repairjson.repair("{'a': +5}") == '{"a":5}'
    assert repairjson.repair("{'a': -5}") == '{"a":-5}'
    assert repairjson.repair("{'a': -1.25}") == '{"a":-1.25}'
    assert repairjson.repair("{'a': -1e3}") == '{"a":-1e3}'
    assert repairjson.repair("{'a': 1e}") == '{"a":1e0}'
    assert repairjson.repair("{'a': 1e+}") == '{"a":1e+0}'
    assert repairjson.repair("{'a': 01}") == '{"a":1}'
    assert repairjson.repair("{'a': 00.5}") == '{"a":0.5}'
    assert repairjson.repair("{'a': 1..2}") == '{"a":"1..2"}'


def test_loads_returns_python_objects():
    assert repairjson.loads("{'a': True, b: [1, 2, 3,]}") == {
        "a": True,
        "b": [1, 2, 3],
    }


def test_prefers_structural_json_after_chatty_preamble():
    assert repairjson.repair("result = {a:1}") == '{"a":1}'
    assert (
        repairjson.repair("Here is the JSON:\n```json\n{a:1}\n```")
        == '{"a":1}'
    )
    assert repairjson.repair("### JSON\n{a:1}") == '{"a":1}'
    assert repairjson.repair("- JSON follows\n{a:1}") == '{"a":1}'
    assert repairjson.repair("1. JSON follows\n[1,2]") == "[1,2]"
    assert repairjson.repair("Items follow: [1,2,3]") == "[1,2,3]"
    assert repairjson.repair("I'm sorry, here is JSON: {a:1}") == '{"a":1}'
    assert repairjson.repair("Note: 'quoted preamble' {a:1}") == '{"a":1}'
    assert (
        repairjson.repair("Note: '{not the payload}' {a:1}")
        == '{"a":1}'
    )
