# Benchmark protocol

## Research questions

**Case 01:** For a whole-day date range, does replacing repeated `DATEDIFF` computations on `orders.ordered_at` with a half-open range reduce query latency when an index on `ordered_at` is present?

**Case 02:** For a report needing line count and gross value per completed order, does consolidating two correlated lookups into one grouped join reduce elapsed time without losing any rows or changing aggregates?

Performance is a hypothesis, not a guaranteed result. The optimizer may decorrelate subqueries, use parallelism, rewrite predicates, or select different access paths.

## Controls

- Same synthetic data and indexes for each variant.
- Same date window and filtered order status.
- No concurrent workload intentionally started by the harness.
- Include a warmup before recorded runs.
- Alternate ordering: baseline/optimized, then optimized/baseline.
- Include full client fetch in both measurements.
- Never drop the optimizer cache or buffer cache (unsafe/shared-host interference).
- Report **all measured values** instead of selecting the fastest run.

## Semantic safety gate

The Python `Counter(tuple(row))` comparison verifies that the full result multiset is identical, including duplicate multiplicity. Missing/extra row instances cause a failure **before benchmarks proceed**. Matching hash values or matching aggregate totals alone are not accepted as equivalent.

Run `SQLLAB_INTEGRATION=1 pytest -q` for full-2024, multi-month and single-day windows. Default `pytest` without SQL Server executes static tests and skips integrations.

## Measurement output

`python -m perf_lab benchmark --iterations 7 --warmups 2` records:

- UTC timestamp, Python version, OS/architecture and dataset sizes.
- Query names and parameters.
- Warmup count and each measured wall-clock runtime (milliseconds).
- Median, interpolated p95, min/max, observed speedup ratio and percent change.
- Full-row multiset equivalence verdict and row cardinality.

**Interpretation:** These are user-observed client timings, not isolated server CPU metrics. P95 calculated from 7 samples is especially weak statistically; use more samples for a robust latency tail estimate.

## Deep-dive in SSMS

To verify mechanism, capture actual execution plans (Ctrl+M) for each variant, and run `SET STATISTICS IO, TIME ON` separately. Compare index seek vs scan, logical reads, execution count, memory grants, spills and elapsed/CPU times. The Python benchmark harness **does not yet automate** SQL Server plan capture.

## Reproducibility limitations

Hardware, Docker virtualization, cache state, SQL Server patch version, degree of parallelism, tempdb and concurrent processes can change results. Never reuse someone else's timing as your own measurement. The GitHub CI benchmark is an integration smoke check, **not** a stable performance regression gate.
