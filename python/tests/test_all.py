import json

import json_repair_rs


def test_repair_smoke():
    payload = '{"status": "ok"}'
    assert json.loads(json_repair_rs.repair(payload)) == {"status": "ok"}


def test_repair_to_string_smoke():
    payload = '{"answer": 42}'
    assert json.loads(json_repair_rs.repair_to_string(payload)) == {"answer": 42}


def test_repair_json_smoke():
    payload = '{"nested": {"value": true}}'
    assert json.loads(json_repair_rs.repair_json(payload)) == {
        "nested": {"value": True}
    }


def test_repairs_target_cases():
    assert json_repair_rs.repair("{'a': 'b'}") == '{"a":"b"}'
    assert (
        json_repair_rs.repair("{'a': True, 'b': False, 'c': None}")
        == '{"a":true,"b":false,"c":null}'
    )
    assert json_repair_rs.repair("{a: 1, b: 2}") == '{"a":1,"b":2}'
    assert json_repair_rs.repair('{"a": 1,}') == '{"a":1}'
    assert json_repair_rs.repair('{"a": 1 "b": 2}') == '{"a":1,"b":2}'
    assert json_repair_rs.repair('{"a": [1, 2, 3}') == '{"a":[1,2,3]}'
    assert json_repair_rs.repair('```json\n{"a": 1}\n```') == '{"a":1}'
    assert json_repair_rs.repair('{"a": "hello\nworld"}') == '{"a":"hello\\nworld"}'


def test_loads_returns_python_objects():
    assert json_repair_rs.loads("{'a': True, b: [1, 2, 3,]}") == {
        "a": True,
        "b": [1, 2, 3],
    }
