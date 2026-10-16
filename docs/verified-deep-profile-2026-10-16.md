# Verified SQL Server CPU, Logical Reads and Actual Plans · 2026-10-16

**Primary evidence:** [Permanent JSON plus 12 actual SQL Server plans](../evidence/deep-profiles/ci-38943948019/) · [Successful CI run 38943948019](https://github.com/Dicureck/sql-performance-lab/actions/runs/38943948019) · [Profiler source](../src/perf_lab/profile.py) · [Evidence validation code](../scripts/archive_deep_profile.py).

## Reproducible environment

Three **independent GitHub-hosted Linux x86_64 runners** provisioned disposable **SQL Server 2022 Developer 16.0.4305.5, CU27** containers. Each generated precisely **2,000 synthetic customers, 12,000 synthetic orders and 36,000 synthetic order lines**. SQL Server reported **4 CPUs and 3,277 MB of memory**; GitHub-hosted hardware is shared and not a production benchmark host.

Each runner used **two warmups and seven recorded runs per query variant**, alternating A/B and B/A. The complete result multiset matched with **zero missing or extra row instances** for all six comparisons before timings were admitted.

Windows (start inclusive, end exclusive): **Focused** June 1–2, 2024; **Intermediate** March 1–October 1, 2024; **Broad** January 1, 2024–January 1, 2025.

## Logical reads · SQL Server pages

**Median 8-KB page reads** from SQL Server DMV sys.dm_exec_query_stats.last_logical_reads, measured on the uniquely identified SELECT statement.

| Fictional query | Date window | Result rows | Original pages | Rewritten pages | Reduction |
|---|---|---:|---:|---:|---:|
| Date predicate | Focused | 4 | 54 | 3 | **94.4%** |
| Date predicate | Intermediate | 4 | 54 | 33 | **38.9%** |
| Date predicate | Broad | 4 | 54 | 54 | **0%** |
| Report aggregation | Focused | 23 | 165 | 84 | **49.1%** |
| Report aggregation | Intermediate | 5,052 | 207 | 120 | **42.0%** |
| Report aggregation | Broad | 8,571 | 228 | 141 | **38.2%** |

## Median CPU and client timing · milliseconds

CPU is the SQL Server server-side last_worker_time value (microseconds converted to ms). The client elapsed measurement uses Python perf_counter around the entire row fetch.

| Query and window | Original CPU | Rewritten CPU | Original client | Rewritten client |
|---|---:|---:|---:|---:|
| Date / Focused | 1.281 | 0.162 | 1.519 | 0.414 |
| Date / Intermediate | 2.857 | 1.672 | 3.161 | 1.965 |
| Date / Broad | 4.754 | 3.478 | 5.218 | 3.995 |
| Aggregation / Focused | 5.981 | 3.548 | 6.215 | 3.872 |
| Aggregation / Intermediate | 13.192 | 8.602 | 16.404 | 16.213 |
| Aggregation / Broad | 21.911 | 15.510 | 36.498 | 36.774 |

The broad-range aggregation rewrite reduced SQL Server logical reads and CPU while **slightly increasing client elapsed time** in this particular runner. It is not accurate to call every rewrite universally faster. Full row transfer and shared-runner variance materially affect these small client-time differences.

## Actual execution plan findings

- The original DATEDIFF predicate produced an **Index Scan** in every window; the rewritten half-open date predicate produced an **Index Seek**.
- On the full-year range, **both date plans read 54 logical pages**. An Index Seek is not necessarily cheaper than an Index Scan for a wide date range.
- The baseline aggregation plan contained **two Clustered Index Scans, two Merge Joins and two Stream Aggregates**, whereas the rewritten plan contained **one each**. Reported logical reads fell across all three windows.
- All **12 saved plans include actual runtime counters**. No ShowPlan warning nodes were reported in these synthetic captures.

The actual plan XML was captured through SET STATISTICS XML ON **after** measured runs. These are real additional query executions, **not guaranteed to be the same plan instance from every earlier DMV-measured trial**.

## Permanent machine-readable evidence

- [Manifest with provenance and medians](../evidence/deep-profiles/ci-38943948019/manifest.json)
- [Focused raw seven-run samples](../evidence/deep-profiles/ci-38943948019/focused/profile.json) · [Index Scan plan](../evidence/deep-profiles/ci-38943948019/focused/date_filter-baseline.actual.sqlplan) · [Index Seek plan](../evidence/deep-profiles/ci-38943948019/focused/date_filter-optimized.actual.sqlplan)
- [Intermediate raw seven-run samples](../evidence/deep-profiles/ci-38943948019/intermediate/profile.json) · [aggregation original plan](../evidence/deep-profiles/ci-38943948019/intermediate/report_aggregation-baseline.actual.sqlplan) · [aggregation rewrite plan](../evidence/deep-profiles/ci-38943948019/intermediate/report_aggregation-optimized.actual.sqlplan)
- [Broad raw seven-run samples](../evidence/deep-profiles/ci-38943948019/broad/profile.json) · [all four plans](../evidence/deep-profiles/ci-38943948019/broad/)

Each raw profile preserves seven ordered observations per variant, full multiset-equivalence metadata, server CPU/elapsed time, client time, logical and physical reads, query hashes, plan operator summaries and run metadata. The entire CI evidence directory was archived automatically only after all three independent runners passed.

## Reproduce in isolated local SQL Server

~~~bash
# Set your own strong SQLLAB_PASSWORD in a local gitignored .env first.
docker compose up -d
python -m perf_lab init --customers 2000 --orders 12000 --lines-per-order 3
SQLLAB_INTEGRATION=1 python -m pytest -q
python -m perf_lab.profile --window focused --warmups 2 --iterations 7 --out results/deep-focused
~~~

## Observed sample variability

The [separate variability report](variability-2026-10-16.md) computes sample standard deviation, coefficient of variation, median absolute deviation and ranges for **all 24 timing-series cells** (3 windows × 2 queries × 2 variants × CPU/client timing). The seven-sample p95 is explicitly labelled too weak for a robust tail-latency claim. Large percent differences can coexist with high relative variability for sub-millisecond query durations.

## Scope and limitations

- Three independent runners covered **different date windows**, not repeated deployments of the identical window. There are seven **within-run** samples per variant, but no independent cross-run confidence interval for the same workload.
- The median and range are useful; the seven-observation **p95 is not statistically robust**.
- Sample data, index design, query optimizer version, cache state, container CPU/memory limits, row-transfer cost and host contention strongly influence the outcome.
- No buffer/plan cache clearing was performed, and no speedup threshold was imposed.
- No real client datasets, proprietary SQL, production measurements, customer systems or credentials were used. Docker volumes were removed at each runner's conclusion.
- These measurements do not certify concurrency throughput, query latency SLAs, a production optimization or universally applicable benefits.

[Earlier client-time smoke benchmark](verified-ci-benchmark-2026-10-15.md) · [Methodology](methodology.md) · [Case studies](case-studies.md)
