# Verified SQL Server CI Benchmark · 2026-10-15

**Evidence source:** [Permanent version-controlled raw measurements](../evidence/ci-benchmark-2026-10-15.json) · [Successful GitHub Actions run #38784723221](https://github.com/Dicureck/sql-performance-lab/actions/runs/38784723221) · [Download original `sql-lab-results` artifact](https://github.com/Dicureck/sql-performance-lab/actions/runs/38784723221/artifacts/11997006659).

**Engine:** Microsoft SQL Server 16.0.4305.5, Developer Edition (64-bit), ephemeral Linux x86_64 container. **Python:** 3.11.17. **Measurement:** client wall-clock elapsed time including result transfer. **Data:** 2,000 synthetic customers, 12,000 synthetic orders and 36,000 synthetic order lines.

**Query window:** `2024-03-01` inclusive to `2024-10-01` exclusive. One warmup and **three measured runs per variant**. The CI system is shared infrastructure; timing variation is expected.

## Measured evidence

| Synthetic case | Full-row equivalent? | Rows | Baseline median | Rewritten median | Relative reduction in this run |
|---|---|---:|---:|---:|---:|
| Date predicate | Yes; 0 missing/extra row instances | 4 | 3.136 ms | 1.928 ms | 38.52% |
| Correlated aggregation | Yes; 0 missing/extra row instances | 5,052 | 17.929 ms | 16.117 ms | 10.11% |

### Individual client-time observations (milliseconds)

| Case | Baseline 1/2/3 | Candidate 1/2/3 |
|---|---|---|
| Date predicate | 3.136 / 3.099 / 3.175 | 1.928 / 1.921 / 1.930 |
| Aggregation | 16.255 / 22.924 / 17.929 | 16.702 / 16.117 / 16.031 |

The permanently versioned JSON (copied from the successful CI artifact) also records p95 values, SQL Server edition/version, number of warmups, and duplicate-aware validation metadata. Percent reductions above are **observations from this single test**, not a performance guarantee or a general claim about SQL Server.

## What is and is not proved

**Verified:** SQL Server container boot, generated data seed, project integration tests, full-row multiset comparison for the measured windows, and a three-run client-time smoke benchmark.

**Not yet verified:** real client workloads, production environments, statistical generality from multiple independent CI runners, actual plan comparison, detailed logical reads, and workload-level optimization impacts.

## Reproduce

Use the [README quickstart](../README.md) with an isolated local database, then:

~~~bash
SQLLAB_INTEGRATION=1 python -m pytest -q
python -m perf_lab benchmark --iterations 3 --warmups 1 --out results/benchmark.json
~~~

Run more iterations and capture actual plans to increase confidence. Never connect this project to a company/production database.
