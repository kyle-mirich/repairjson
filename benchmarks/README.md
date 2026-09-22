# Benchmarks

These are synthetic repair-to-string throughput measurements, not an accuracy evaluation or a promise about production workloads. The comparison package has broader repair heuristics; matching outputs on the included fixtures does not imply API or behavioral compatibility.

## Reproduce

Use a release build. `uv pip install -e` builds the extension with Maturin's release profile; if you use `maturin develop` directly, pass `--release`.

```bash
uv venv --python 3.12
uv pip install -e ".[dev,benchmark]"
.venv/bin/python benchmark.py --megabytes 1 --repeat 5 --output benchmarks/local.json
```

The original corpus size remains the default (20 MiB per profile):

```bash
.venv/bin/python benchmark.py --dataset all --repeat 3
```

Use `--dataset dense_object` for one profile and `--verify-samples 1000` for more equivalence checks. Generated corpora live in `benchmarks/generated/` and are ignored by Git. They are regenerated each run, so changes to sample generators cannot reuse stale fixtures.

## Method

- Each corpus contains many independent small records, separated by a record-separator byte. A 20 MiB corpus is **not** a single 20 MiB JSON document.
- `repairjson.repair` and `json_repair.repair_json(..., skip_json_loads=True)` both return JSON strings. Decoding, dataset generation, verification, and disk access are outside the timed loops.
- Before timing, decoded results are compared for 100 records spread across each corpus. Increase the sample count for stronger fixture verification; it is not a general correctness proof.
- Both implementations receive 100 warmup calls. Timing order alternates between repeats. The JSON report includes every sample, median durations, package versions, interpreter version, and platform metadata.
- Short native timings are sensitive to CPU scheduling and clock resolution. Use larger corpora and an otherwise idle machine for performance decisions. This harness does not measure peak memory, threading scalability, or adversarial large-document latency.

## Recorded sample

[Raw report](results/0.2.0-macos-arm64.json), collected on 2026-09-21 (local time) on an Apple M4, macOS 26.6.2, CPython 3.14.0; `repairjson` 0.2.0 and `json-repair` 0.63.4. One MiB per corpus, five repeats, median wall-clock seconds. Results will vary by machine and input.

| Profile | Records | json-repair (s) | repairjson (s) | Ratio |
| --- | ---: | ---: | ---: | ---: |
| `dense_object` | 9,280 | 0.7105 | 0.0040 | 178.1× |
| `fenced_payload` | 9,893 | 0.6541 | 0.0040 | 164.4× |
| `chatty_nested` | 5,141 | 0.7384 | 0.0039 | 188.7× |
| `long_text` | 4,069 | 0.7505 | 0.0033 | 225.7× |
| `array_heavy` | 6,564 | 0.8009 | 0.0050 | 160.4× |
| `truncated_nested` | 5,047 | 0.8483 | 0.0044 | 191.6× |
