"""Exercise the installed API in a disposable process; no external services required."""

import argparse
import json
import random

import repairjson


def check_boundaries() -> None:
    functions = (
        repairjson.repair,
        repairjson.repair_json,
        repairjson.repair_to_string,
        repairjson.loads,
    )
    for function in functions:
        for source in ("[" * 100_000, '{"a":' * 100_000):
            try:
                function(source)
            except ValueError as error:
                assert "nesting exceeds" in str(error)
            else:
                raise AssertionError("Expected depth error")
        for surrogate in ("\ud800", "\udfff", "x\ud800y"):
            try:
                function(surrogate)
            except UnicodeError:
                pass
            else:
                raise AssertionError("Expected Unicode error")
        for source in ('"\\ud800"', '"\\udfff"', '"\\ud83d\\ude42"'):
            expected = json.loads(source)
            result = function(source)
            assert (result if function is repairjson.loads else json.loads(result)) == expected
        assert function("{ok: True}") in ('{"ok":true}', {"ok": True})


def check_large_inputs() -> int:
    sources = [
        "[" + "0," * 100_000,
        '{a:"' + "\x00" * 200_000,
        "/*" + "*" * 1_000_000,
        "[1/*" + "x" * 1_000_000,
        '"' + "\\🙂" * 100_000,
        '"' + "\\u" * 100_000,
        '{a:"value"/*' + "x" * 1_000_000,
    ]
    for source in sources:
        repaired = repairjson.repair(source)
        json.loads(repaired)
        assert repairjson.repair(repaired) == repaired
    return len(sources)


def check_noise(cases: int, seed: int) -> dict:
    rng = random.Random(seed)
    alphabet = "{}[]:,\\\"'0123456789.eE+-truefalsnN \n\t\x00中🙂"
    rejected = 0
    for _ in range(cases):
        source = "".join(rng.choices(alphabet, k=rng.randrange(400)))
        try:
            repaired = repairjson.repair(source)
        except ValueError as error:
            assert "Ambiguous unescaped quote" in str(error) or "nesting exceeds" in str(error)
            rejected += 1
            continue
        json.loads(repaired)
        assert repairjson.repair(repaired) == repaired
    assert repairjson.loads("{ok: True}") == {"ok": True}
    return {
        "seed": seed,
        "cases": cases,
        "max_input_characters": 399,
        "accepted": cases - rejected,
        "documented_value_errors": rejected,
    }


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=positive_integer, default=10_000)
    parser.add_argument("--seed", type=int, default=76381)
    args = parser.parse_args()
    check_boundaries()
    large_cases = check_large_inputs()
    report = check_noise(args.cases, args.seed)
    print(json.dumps({"repairjson": repairjson.__version__, "large_cases": large_cases, **report}))


if __name__ == "__main__":
    main()
