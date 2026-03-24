#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import json_repair
import json_repair_rs

RECORD_SEPARATOR = "\x1e\n"


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    sample_factory: Callable[[int], str]
    target_megabytes: int
    verify_equivalence: bool = True


def dense_object_sample(index: int) -> str:
    user = f"user_{index % 10}"
    return (
        "{user: '"
        + user
        + "', active: True, score: 12.5, tags: ['x', 'y',], meta: "
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


PROFILES = {
    "dense_object": DatasetProfile(
        name="dense_object",
        sample_factory=dense_object_sample,
        target_megabytes=20,
    ),
    "fenced_payload": DatasetProfile(
        name="fenced_payload",
        sample_factory=fenced_payload_sample,
        target_megabytes=20,
    ),
    "chatty_nested": DatasetProfile(
        name="chatty_nested",
        sample_factory=chatty_nested_sample,
        target_megabytes=20,
    ),
}


def generate_dataset(profile: DatasetProfile, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{profile.name}_{profile.target_megabytes}mb.rsbench"
    target_bytes = profile.target_megabytes * 1024 * 1024

    if path.exists() and path.stat().st_size >= target_bytes:
        return path

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


def benchmark_lines(path: Path) -> dict[str, float]:
    lines = read_records(path)

    start = time.perf_counter()
    for line in lines:
        json_repair.repair_json(line, skip_json_loads=True)
    python_seconds = time.perf_counter() - start

    start = time.perf_counter()
    for line in lines:
        json_repair_rs.repair(line)
    rust_seconds = time.perf_counter() - start

    return {
        "python_seconds": python_seconds,
        "rust_seconds": rust_seconds,
        "speedup": python_seconds / rust_seconds,
        "line_count": float(len(lines)),
        "bytes": float(path.stat().st_size),
    }


def verify_outputs(path: Path) -> None:
    for line in read_records(path)[:100]:
        python_output = json_repair.repair_json(line, skip_json_loads=True)
        rust_output = json_repair_rs.repair(line)
        if json.loads(python_output) != json.loads(rust_output):
            raise AssertionError(
                "Rust repair output diverged semantically from python json_repair "
                "within the verification sample."
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["all", *PROFILES.keys()],
        default="all",
        help="Dataset profile to benchmark.",
    )
    parser.add_argument(
        "--data-dir",
        default="benchmarks/generated",
        help="Directory for generated benchmark corpora.",
    )
    args = parser.parse_args()

    selected = (
        PROFILES.values()
        if args.dataset == "all"
        else [PROFILES[args.dataset]]
    )

    results = []
    data_root = Path(args.data_dir)

    for profile in selected:
        path = generate_dataset(profile, data_root)
        metrics = benchmark_lines(path)
        if profile.verify_equivalence:
            verify_outputs(path)

        results.append(
            {
                "dataset": profile.name,
                "path": str(path),
                "bytes": int(metrics["bytes"]),
                "line_count": int(metrics["line_count"]),
                "python_seconds": round(metrics["python_seconds"], 6),
                "rust_seconds": round(metrics["rust_seconds"], 6),
                "speedup": round(metrics["speedup"], 2),
            }
        )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
