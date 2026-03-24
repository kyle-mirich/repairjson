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


def test_loads_returns_python_objects():
    assert repairjson.loads("{'a': True, b: [1, 2, 3,]}") == {
        "a": True,
        "b": [1, 2, 3],
    }
