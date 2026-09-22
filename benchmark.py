#!/usr/bin/env python3
"""Compare repair-to-string throughput on deterministic synthetic records."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import json_repair
import repairjson

RECORD_SEPARATOR = "\x1e\n"


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    sample_factory: Callable[[int], str]


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


PROFILES = {
    "dense_object": DatasetProfile(
        name="dense_object",
        sample_factory=dense_object_sample,
    ),
    "fenced_payload": DatasetProfile(
        name="fenced_payload",
        sample_factory=fenced_payload_sample,
    ),
    "chatty_nested": DatasetProfile(
        name="chatty_nested",
        sample_factory=chatty_nested_sample,
    ),
    "long_text": DatasetProfile(
        name="long_text",
        sample_factory=long_text_sample,
    ),
    "array_heavy": DatasetProfile(
        name="array_heavy",
        sample_factory=array_heavy_sample,
    ),
    "truncated_nested": DatasetProfile(
        name="truncated_nested",
        sample_factory=truncated_nested_sample,
    ),
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


def measure(records: list[str], function: Callable[[str], str]) -> float:
    start = time.perf_counter()
    for record in records:
        function(record)
    return time.perf_counter() - start


def python_repair(source: str) -> str:
    return json_repair.repair_json(source, skip_json_loads=True)


def verify_outputs(records: list[str], sample_count: int) -> None:
    # Spread verification over the corpus instead of checking only its prefix.
    count = min(sample_count, len(records))
    for index in range(count):
        record_index = index * len(records) // count
        source = records[record_index]
        if json.loads(python_repair(source)) != json.loads(repairjson.repair(source)):
            raise AssertionError(f"Implementations disagree at record {record_index}")


def benchmark_records(records: list[str], repeat: int) -> dict:
    functions = {"python": python_repair, "rust": repairjson.repair}
    samples = {name: [] for name in functions}
    # Warm both paths before timing; vary order to reduce first-run bias.
    for function in functions.values():
        for record in records[:100]:
            function(record)
    for iteration in range(repeat):
        order = ["python", "rust"] if iteration % 2 == 0 else ["rust", "python"]
        for name in order:
            samples[name].append(measure(records, functions[name]))
    python_seconds = statistics.median(samples["python"])
    rust_seconds = statistics.median(samples["rust"])
    return {
        "python_seconds_median": python_seconds,
        "rust_seconds_median": rust_seconds,
        "speedup": python_seconds / rust_seconds,
        "samples_seconds": samples,
    }


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
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
    parser.add_argument(
        "--verify-samples",
        type=positive_integer,
        default=100,
        help="Records checked for semantic equivalence before timing.",
    )
    parser.add_argument("--output", type=Path, help="Also save the JSON report to this file.")
    args = parser.parse_args()

    selected = PROFILES.values() if args.dataset == "all" else [PROFILES[args.dataset]]
    results = []
    for profile in selected:
        path = generate_dataset(profile, Path(args.data_dir), args.megabytes)
        records = read_records(path)
        verify_outputs(records, args.verify_samples)
        metrics = benchmark_records(records, args.repeat)
        results.append(
            {
                "dataset": profile.name,
                "bytes": path.stat().st_size,
                "record_count": len(records),
                "verified_records": min(args.verify_samples, len(records)),
                **metrics,
            }
        )

    report = {
        "environment": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "repairjson": version("repairjson"),
            "json-repair": version("json-repair"),
        },
        "method": {
            "mebibytes_per_dataset": args.megabytes,
            "repeat": args.repeat,
            "statistic": "median",
            "comparison": "repair-to-string; json-repair skip_json_loads=True",
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
