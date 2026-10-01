"""Benchmark failures must be visible before a performance claim is produced."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import repairjson

spec = importlib.util.spec_from_file_location(
    "repairjson_benchmark", Path(__file__).resolve().parents[2] / "benchmark.py"
)
benchmark = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = benchmark
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize("profile", benchmark.PROFILES.values(), ids=benchmark.PROFILES)
def test_benchmark_fixtures_have_explicit_expected_values(profile):
    records = [profile.sample_factory(index) for index in range(40)]
    benchmark.verify_outputs(records, len(records), profile, {"repairjson": repairjson.repair})


def test_agreement_between_implementations_is_not_enough():
    profile = benchmark.PROFILES["dense_object"]
    functions = {"first": lambda _: "null", "second": lambda _: "null"}
    with pytest.raises(AssertionError, match="first disagrees with expected value at record 0"):
        benchmark.verify_outputs([profile.sample_factory(0)], 1, profile, functions)


def test_sample_verification_includes_last_record():
    profile = benchmark.PROFILES["dense_object"]
    records = [profile.sample_factory(index) for index in range(3)] + ["null"]
    with pytest.raises(AssertionError, match="record 3"):
        benchmark.verify_outputs(records, 2, profile, {"repairjson": repairjson.repair})


def test_calibrated_samples_are_normalized_and_separator_bytes_are_excluded(monkeypatch):
    # Simulate implementations with different rates without timing a scheduler in a unit test.
    fast = lambda _: None  # noqa: E731
    slow = lambda _: None  # noqa: E731
    durations = {fast: 0.01, slow: 0.1}
    monkeypatch.setattr(
        benchmark, "measure", lambda records, function, batches=1: durations[function] * batches
    )
    report = benchmark.benchmark_records(["🙂", "a"], 3, {"repairjson": fast, "slow": slow}, 0.2)
    assert report["input_bytes"] == 5
    assert report["ratio_to_repairjson"]["slow"] == 10
    assert report["implementations"]["repairjson"]["batches_per_sample"] == 32
    assert report["implementations"]["slow"]["batches_per_sample"] == 2
    assert all(t >= 0.2 for t in report["implementations"]["repairjson"]["samples_seconds"])
    assert report["execution_orders"] == [
        ["repairjson", "slow"],
        ["slow", "repairjson"],
        ["repairjson", "slow"],
    ]
    assert report["implementations"]["repairjson"]["records_per_second"] == 200


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_invalid_timing_targets_are_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        benchmark.positive_seconds(value)


def test_generated_corpus_is_utf8_and_regenerated(tmp_path):
    profile = benchmark.PROFILES["unicode"]
    path = benchmark.generate_dataset(profile, tmp_path, 1)
    records = benchmark.read_records(path)
    assert path.stat().st_size >= 1024**2
    assert records[0] == profile.sample_factory(0)
    assert records[-1] == profile.sample_factory(len(records) - 1)
    path.write_text("stale content")
    assert benchmark.read_records(benchmark.generate_dataset(profile, tmp_path, 1)) == records


def test_valid_json_baseline_fixture_is_strict_json():
    profile = benchmark.PROFILES["valid_json"]
    assert profile.valid_json
    assert json.loads(profile.sample_factory(7)) == profile.expected_factory(7)
