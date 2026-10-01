#!/usr/bin/env python3
"""Compare repair-to-string throughput on deterministic synthetic records."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import repairjson

RECORD_SEPARATOR = "\x1e\n"


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    sample_factory: Callable[[int], str]
    expected_factory: Callable[[int], object]
    valid_json: bool = False


def dense_object_sample(index: int) -> str:
    user = f"user_{index % 10}"
    return (
        "{user: '" + user + "', active: True, score: 12.5, tags: ['x', 'y',], meta: "
        "{retry: False note: 'line one\\nline two'}}"
    )


def fenced_payload_sample(index: int) -> str:
    step = index % 4
    return (
        "```json\n"
        "{model: 'gpt-5', output: [{step: "
        + str(step)
        + " result: 'ok',}, {step: "
        + str(step + 1)
        + " result: 'retry',}], done: False}\n```"
    )


def chatty_nested_sample(index: int) -> str:
    prompt_tokens = 12 + (index % 7)
    completion_tokens = 34 + (index % 11)
    total_tokens = prompt_tokens + completion_tokens
    return (
        "{message: 'hello\\nworld', choices: [{index: 0 text: 'foo', finish_reason: 'stop',}, "
        "{index: 1 text: 'bar', finish_reason: 'length',}], usage: {prompt_tokens: "
        + str(prompt_tokens)
        + " completion_tokens: "
        + str(completion_tokens)
        + " total_tokens: "
        + str(total_tokens)
        + "},}"
    )


def long_text_sample(index: int) -> str:
    section = index % 5
    return (
        "{id: "
        + str(index)
        + ", title: 'Report "
        + str(section)
        + "', summary: 'Paragraph one with context\\nParagraph two with more context\\n"
        + "Paragraph three with quoted words and symbols like : and , inside the text', "
        + "notes: ['alpha line\\nbeta line', 'gamma',], approved: False, owner: 'pending'}"
    )


def array_heavy_sample(index: int) -> str:
    base = index % 100
    return (
        "[{kind: 'event', id: "
        + str(base)
        + " status: 'ok', score: 1.25}, "
        + "{kind: 'event', id: "
        + str(base + 1)
        + " status: 'retry', score: 2.5,}, "
        + "{kind: 'event', id: "
        + str(base + 2)
        + " status: 'done', score: 3.75}]"
    )


def truncated_nested_sample(index: int) -> str:
    turn = index % 8
    return (
        "{session: {id: 'sess_"
        + str(turn)
        + "', messages: [{role: 'system', content: 'You are helpful'}, "
        + "{role: 'user', content: 'question "
        + str(index)
        + "'}, {role: 'assistant', content: 'partial answer', metadata: {safe: True, retries: 0}}"
    )


def dense_object_expected(index: int) -> dict:
    return {
        "user": f"user_{index % 10}",
        "active": True,
        "score": 12.5,
        "tags": ["x", "y"],
        "meta": {"retry": False, "note": "line one\nline two"},
    }


def fenced_payload_expected(index: int) -> dict:
    step = index % 4
    return {
        "model": "gpt-5",
        "output": [{"step": step, "result": "ok"}, {"step": step + 1, "result": "retry"}],
        "done": False,
    }


def chatty_nested_expected(index: int) -> dict:
    prompt, completion = 12 + index % 7, 34 + index % 11
    return {
        "message": "hello\nworld",
        "choices": [
            {"index": 0, "text": "foo", "finish_reason": "stop"},
            {"index": 1, "text": "bar", "finish_reason": "length"},
        ],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        },
    }


def long_text_expected(index: int) -> dict:
    return {
        "id": index,
        "title": f"Report {index % 5}",
        "summary": "Paragraph one with context\nParagraph two with more context\n"
        "Paragraph three with quoted words and symbols like : and , inside the text",
        "notes": ["alpha line\nbeta line", "gamma"],
        "approved": False,
        "owner": "pending",
    }


def array_heavy_expected(index: int) -> list:
    base = index % 100
    return [
        {"kind": "event", "id": base, "status": "ok", "score": 1.25},
        {"kind": "event", "id": base + 1, "status": "retry", "score": 2.5},
        {"kind": "event", "id": base + 2, "status": "done", "score": 3.75},
    ]


def truncated_nested_expected(index: int) -> dict:
    return {
        "session": {
            "id": f"sess_{index % 8}",
            "messages": [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": f"question {index}"},
                {
                    "role": "assistant",
                    "content": "partial answer",
                    "metadata": {"safe": True, "retries": 0},
                },
            ],
        }
    }


def unicode_sample(index: int) -> str:
    return "{名字: '你好🙂', café: 'résumé', id: " + str(index) + ", tags: ['東京', '🌍',]}"


def unicode_expected(index: int) -> dict:
    return {"名字": "你好🙂", "café": "résumé", "id": index, "tags": ["東京", "🌍"]}


def valid_json_sample(index: int) -> str:
    return json.dumps(dense_object_expected(index), ensure_ascii=False, separators=(",", ":"))


PROFILES = {
    "dense_object": DatasetProfile(
        name="dense_object",
        sample_factory=dense_object_sample,
        expected_factory=dense_object_expected,
    ),
    "fenced_payload": DatasetProfile(
        name="fenced_payload",
        sample_factory=fenced_payload_sample,
        expected_factory=fenced_payload_expected,
    ),
    "chatty_nested": DatasetProfile(
        name="chatty_nested",
        sample_factory=chatty_nested_sample,
        expected_factory=chatty_nested_expected,
    ),
    "long_text": DatasetProfile(
        name="long_text",
        sample_factory=long_text_sample,
        expected_factory=long_text_expected,
    ),
    "array_heavy": DatasetProfile(
        name="array_heavy",
        sample_factory=array_heavy_sample,
        expected_factory=array_heavy_expected,
    ),
    "truncated_nested": DatasetProfile(
        name="truncated_nested",
        sample_factory=truncated_nested_sample,
        expected_factory=truncated_nested_expected,
    ),
    "unicode": DatasetProfile("unicode", unicode_sample, unicode_expected),
    "valid_json": DatasetProfile("valid_json", valid_json_sample, dense_object_expected, True),
}


def generate_dataset(profile: DatasetProfile, root: Path, megabytes: int) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{profile.name}_{megabytes}mib.rsbench"
    target_bytes = megabytes * 1024 * 1024

    size = 0
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        while size < target_bytes:
            record = profile.sample_factory(index) + RECORD_SEPARATOR
            handle.write(record)
            size += len(record.encode("utf-8"))
            index += 1

    return path


def read_records(path: Path) -> list[str]:
    records = path.read_text(encoding="utf-8").split(RECORD_SEPARATOR)
    return [record for record in records if record]


def measure(records: list[str], function: Callable[[str], str], batches: int = 1) -> float:
    start = time.perf_counter()
    for _ in range(batches):
        for record in records:
            function(record)
    return time.perf_counter() - start


def comparison_functions(valid_json: bool) -> dict[str, Callable[[str], str]]:
    # Import only when running the comparison. Core tests need no benchmark extra.
    import json_repair

    functions = {
        "repairjson": repairjson.repair,
        "json_repair_skip": lambda source: json_repair.repair_json(
            source, skip_json_loads=True, ensure_ascii=False, separators=(",", ":")
        ),
        "json_repair_default": lambda source: json_repair.repair_json(
            source, ensure_ascii=False, separators=(",", ":")
        ),
    }
    if valid_json:
        # Same string-to-string contract, but this baseline cannot repair malformed input.
        functions["json_roundtrip"] = lambda source: json.dumps(
            json.loads(source), ensure_ascii=False, separators=(",", ":")
        )
    return functions


def verify_outputs(
    records: list[str],
    sample_count: int,
    profile: DatasetProfile,
    functions: dict[str, Callable[[str], str]],
) -> None:
    # Spread verification over the corpus instead of checking only its prefix.
    count = min(sample_count, len(records))
    for index in range(count):
        record_index = index * (len(records) - 1) // max(count - 1, 1)
        source = records[record_index]
        expected = profile.expected_factory(record_index)
        for name, function in functions.items():
            if json.loads(function(source)) != expected:
                raise AssertionError(
                    f"{name} disagrees with expected value at record {record_index}"
                )


def calibrate_batches(
    records: list[str], function: Callable[[str], str], min_seconds: float
) -> int:
    batches = 1
    while measure(records, function, batches) < min_seconds:
        batches *= 2
        if batches > 1_048_576:
            raise RuntimeError("Timing calibration failed; use a larger corpus")
    return batches


def benchmark_records(
    records: list[str],
    repeat: int,
    functions: dict[str, Callable[[str], str]],
    min_seconds: float,
) -> dict:
    samples = {name: [] for name in functions}
    # Warm each path and calibrate enough whole-corpus batches for useful timings.
    for function in functions.values():
        for record in records[:100]:
            function(record)
    batches = {
        name: calibrate_batches(records, function, min_seconds)
        for name, function in functions.items()
    }
    names = list(functions)
    execution_orders = []
    for iteration in range(repeat):
        offset = iteration % len(names)
        order = names[offset:] + names[:offset]
        execution_orders.append(order)
        for name in order:
            samples[name].append(measure(records, functions[name], batches[name]))
    input_bytes = sum(len(record.encode("utf-8")) for record in records)
    implementations = {}
    for name, timings in samples.items():
        per_corpus = [elapsed / batches[name] for elapsed in timings]
        median = statistics.median(per_corpus)
        implementations[name] = {
            "batches_per_sample": batches[name],
            "samples_seconds": timings,
            "seconds_per_corpus_median": median,
            "records_per_second": len(records) / median,
            "input_mib_per_second": input_bytes / 1024**2 / median,
        }
    rust_seconds = implementations["repairjson"]["seconds_per_corpus_median"]
    return {
        "input_bytes": input_bytes,
        "implementations": implementations,
        "ratio_to_repairjson": {
            name: metrics["seconds_per_corpus_median"] / rust_seconds
            for name, metrics in implementations.items()
            if name != "repairjson"
        },
        "execution_orders": execution_orders,
    }


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def positive_seconds(value: str) -> float:
    parsed = float(value)
    if not 0 < parsed < float("inf"):
        raise argparse.ArgumentTypeError("must be finite and positive")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["all", *PROFILES], default="all")
    parser.add_argument("--data-dir", default="benchmarks/generated")
    parser.add_argument(
        "--megabytes",
        type=positive_integer,
        default=20,
        help="MiB of small records per profile (not one large document).",
    )
    parser.add_argument("--repeat", type=positive_integer, default=3)
    parser.add_argument("--min-seconds", type=positive_seconds, default=0.2)
    parser.add_argument(
        "--build-label", default="unspecified", help="Record how the extension was built"
    )
    parser.add_argument(
        "--verify-samples",
        type=positive_integer,
        default=None,
        help="Verify this many spread-out records; default checks every record.",
    )
    parser.add_argument("--output", type=Path, help="Also save the JSON report to this file.")
    args = parser.parse_args()

    selected = PROFILES.values() if args.dataset == "all" else [PROFILES[args.dataset]]
    results = []
    for profile in selected:
        path = generate_dataset(profile, Path(args.data_dir), args.megabytes)
        records = read_records(path)
        functions = comparison_functions(profile.valid_json)
        count = args.verify_samples or len(records)
        verify_outputs(records, count, profile, functions)
        metrics = benchmark_records(records, args.repeat, functions, args.min_seconds)
        results.append(
            {
                "dataset": profile.name,
                "corpus_file_bytes": path.stat().st_size,
                "corpus_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "record_count": len(records),
                "verified_records": min(count, len(records)),
                **metrics,
            }
        )

    report = {
        "schema_version": 2,
        "environment": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "repairjson": version("repairjson"),
            "json-repair": version("json-repair"),
            "build_label": args.build_label,
            "source_sha256": {
                name: hashlib.sha256(Path(__file__).parent.joinpath(name).read_bytes()).hexdigest()
                for name in [
                    "benchmark.py",
                    "src/lexer.rs",
                    "src/parser.rs",
                    "src/lib.rs",
                    "Cargo.lock",
                ]
            },
        },
        "method": {
            "mebibytes_per_dataset": args.megabytes,
            "repeat": args.repeat,
            "min_sample_seconds": args.min_seconds,
            "statistic": "median",
            "comparison": (
                "compact UTF-8 string-to-string; json-repair default and skip_json_loads=True"
            ),
            "verification": "decoded values against independent fixture expectations before timing",
            "valid_only_baseline": "json_roundtrip = json.loads + compact UTF-8 json.dumps",
        },
        "results": results,
    }
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
