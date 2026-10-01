# Benchmarks

These are synthetic repair-to-string throughput measurements, not an accuracy evaluation or a promise about production workloads. The comparison package has broader repair heuristics; matching outputs on the included fixtures does not imply API or behavioral compatibility.

## Reproduce

Use a release build. `uv pip install -e` builds the extension with Maturin's release profile; if you use `maturin develop` directly, pass `--release`. The following pins the comparison version used in the current recorded run:

```bash
uv venv --python 3.12
uv pip install -e ".[dev,benchmark]"
uv pip install "json-repair==0.63.5"
.venv/bin/python benchmark.py --megabytes 1 --repeat 5 --min-seconds 0.2 --build-label editable-release --output benchmarks/local.json
```

The original corpus size remains the default (20 MiB per profile):

```bash
.venv/bin/python benchmark.py --dataset all --repeat 3
```

Use `--dataset dense_object` for one profile. Every record is verified by default; `--verify-samples 1000` opts into a spread-out sample including the first and last records. Generated corpora live in `benchmarks/generated/` and are ignored by Git. They are regenerated each run, so changes to sample generators cannot reuse stale fixtures. Reports identify fixture contents and the harness/parser source with SHA-256 hashes.

For an installed-wheel measurement, build with `.venv/bin/maturin build --release --locked -o dist`, install that wheel in a separate environment together with `json-repair==0.63.5`, and run this repository's harness using the separate environment's Python. Set `--build-label release-wheel` to record that choice. The label is supplied by the operator; the harness cannot detect the native build profile. Use the same Python version, comparison dependency, and generated corpus when comparing changes. Do not time an editable debug build against a release wheel.

## Method

- Each corpus contains many independent small records, separated by a record-separator byte. A 20 MiB corpus is **not** a single 20 MiB JSON document.
- Every implementation returns compact JSON text. The Python comparison uses `ensure_ascii=False, separators=(',', ':')` to avoid charging it for ASCII escaping or spaces that the native path does not generate. Its default mode checks valid JSON first; `json_repair_skip` uses `skip_json_loads=True`. Both modes are reported explicitly rather than selecting whichever looks slower.
- The `valid_json` profile also measures `json.loads` followed by compact UTF-8 `json.dumps`. It is a standard-library string-to-string reference on valid input, **not a malformed-input repair baseline**. The other profiles omit it. The Unicode profile exercises actual non-ASCII UTF-8 rather than escape-only ASCII.
- Before timing, each decoded result must match an independently specified fixture value. Two implementations agreeing on a wrong value no longer passes verification. This checks the corpus, not general repair accuracy or equivalence on arbitrary malformed input.
- Each implementation receives 100 warmup calls and an independently calibrated power-of-two count of whole-corpus batches targeting at least `--min-seconds` (default 0.2 seconds). Repeats rotate execution order. Raw sample times and batch counts are saved; medians and ratios are normalized to one corpus. Calibration is outside recorded samples; scheduling can still make a subsequent sample shorter than the target.
- Throughput counts UTF-8 bytes passed to the API, excluding on-disk record separators. Generation, file I/O, verification, and decoding **for verification** are outside timed loops. Python comparison implementations may internally construct Python objects and serialize them; native repair directly writes text. This architectural difference is part of the comparison, not evidence of interchangeable repair policies.
- Reports retain every timing sample, execution order, versions, source/corpus hashes, and platform metadata. Schema version 2 reports differ from the historical report below. Results are local measurements without a universal speedup claim.
- Use larger corpora and an otherwise idle machine for performance decisions. This harness does not measure peak memory, threading scalability, large-document latency, or the overhead of `repairjson.loads()`.

## Calibrated integrity run (shared machine load)

[Raw annotated report](results/0.2.0-calibrated-macos-arm64-loaded.json), collected on 2026-10-01 UTC with a local release wheel, CPython 3.12.12, macOS 26.6.2 arm64, `repairjson` 0.2.0 and `json-repair` 0.63.5. One MiB per profile, five repeats, a 0.2-second calibration target, and complete fixture verification.

All 62,276 records matched their expected values on each repair path; the 9,199 valid records also matched the standard-library roundtrip. The raw report retains the observed timings, but concurrent Rust/Python tasks caused substantial machine pressure (reported load reached 44). Its ratios are **not suitable for speedup or résumé claims**. This run demonstrates the verification and reporting pipeline; collect new measurements on an idle machine for a performance comparison. The operator's conditions annotation was added after collection without changing samples or hashes.

| Profile | Fully verified records |
| --- | ---: |
| `dense_object` | 9,280 |
| `fenced_payload` | 9,893 |
| `chatty_nested` | 5,141 |
| `long_text` | 4,069 |
| `array_heavy` | 6,564 |
| `truncated_nested` | 5,047 |
| `unicode` | 13,083 |
| `valid_json` | 9,199 |

## Historical sample (original method)

[Raw report](results/0.2.0-macos-arm64.json), collected on 2026-09-21 (local time) on an Apple M4, macOS 26.6.2, CPython 3.14.0; `repairjson` 0.2.0 and `json-repair` 0.63.4. One MiB per corpus, five repeats, median wall-clock seconds. Results will vary by machine and input.

This older run used short uncalibrated native timings, only sampled equivalence between implementations, and the comparison package's default output formatting. It is retained for history; use the calibrated run for new performance claims.

| Profile | Records | json-repair (s) | repairjson (s) | Ratio |
| --- | ---: | ---: | ---: | ---: |
| `dense_object` | 9,280 | 0.7105 | 0.0040 | 178.1× |
| `fenced_payload` | 9,893 | 0.6541 | 0.0040 | 164.4× |
| `chatty_nested` | 5,141 | 0.7384 | 0.0039 | 188.7× |
| `long_text` | 4,069 | 0.7505 | 0.0033 | 225.7× |
| `array_heavy` | 6,564 | 0.8009 | 0.0050 | 160.4× |
| `truncated_nested` | 5,047 | 0.8483 | 0.0044 | 191.6× |
