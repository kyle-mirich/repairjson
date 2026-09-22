"""Check invariants with generated values instead of matching parser internals."""

import json

import repairjson
from hypothesis import given, settings
from hypothesis import strategies as st

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda children: (
        st.lists(children, max_size=8) | st.dictionaries(st.text(), children, max_size=8)
    ),
    max_leaves=40,
)


@settings(max_examples=500, deadline=None, derandomize=True)
@given(json_values, st.booleans())
def test_valid_json_preserves_values(value, ensure_ascii):
    source = json.dumps(value, ensure_ascii=ensure_ascii, allow_nan=False)
    repaired = repairjson.repair(source)
    assert json.loads(repaired) == value
    assert repairjson.repair(repaired) == repaired


@settings(max_examples=1000, deadline=None, derandomize=True)
@given(st.text(max_size=1000))
def test_arbitrary_unicode_produces_parseable_idempotent_json(source):
    repaired = repairjson.repair(source)
    json.loads(repaired)
    assert repairjson.repair(repaired) == repaired


@settings(max_examples=1000, deadline=None, derandomize=True)
@given(st.text(alphabet="{}[]:,\\\"'0123456789.eE+-truefalsnN \n\t\x00中🙂", max_size=300))
def test_syntax_noise_produces_valid_json(source):
    repaired = repairjson.repair(source)
    json.loads(repaired)
    assert repairjson.repair(repaired) == repaired


@settings(max_examples=500, deadline=None, derandomize=True)
@given(json_values, st.integers(min_value=0, max_value=10000))
def test_truncated_json_remains_parseable(value, cut):
    source = json.dumps(value)
    repaired = repairjson.repair(source[: cut % (len(source) + 1)])
    json.loads(repaired)
