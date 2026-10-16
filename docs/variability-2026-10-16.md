# Within-run timing variability · October 16, 2026

**Primary source:** [Raw seven-trial SQL Server results](../evidence/deep-profiles/ci-38943948019/) · [successful CI run](https://github.com/Dicureck/sql-performance-lab/actions/runs/38943948019).

This analysis includes **every recorded trial**, rather than selecting the best or fastest execution. Per-cell numbers are from one runner's seven repeated executions of the same query variant and date window.

**Method:** sample standard deviation uses n−1; coefficient of variation (CV) is sample standard deviation / arithmetic mean; median absolute deviation (MAD) is the median of each absolute distance from the run median. These measures describe **within-run stability only**. A sample of seven is insufficient to infer a statistically reliable population p95, superiority p-value or general SLA.

| Window | Case | Variant | Metric | Median ms | Min–max ms | Std dev / mean | MAD ms |
|---|---|---|---|---:|---|---:|---:|
| focused | Date filter | baseline | Client elapsed | 1.519 | 1.433–1.564 | 2.722% | 0.017 |
| focused | Date filter | baseline | Server worker CPU | 1.281 | 1.214–1.294 | 2.171% | 0.008 |
| focused | Date filter | optimized | Client elapsed | 0.414 | 0.335–0.729 | 29.969% | 0.027 |
| focused | Date filter | optimized | Server worker CPU | 0.162 | 0.132–0.392 | 47.547% | 0.013 |
| focused | Aggregation | baseline | Client elapsed | 6.215 | 6.161–6.698 | 3.579% | 0.04 |
| focused | Aggregation | baseline | Server worker CPU | 5.981 | 5.932–6.175 | 1.741% | 0.042 |
| focused | Aggregation | optimized | Client elapsed | 3.872 | 3.682–5.734 | 17.875% | 0.124 |
| focused | Aggregation | optimized | Server worker CPU | 3.548 | 3.472–5.278 | 17.487% | 0.05 |
| intermediate | Date filter | baseline | Client elapsed | 3.161 | 3.12–4.852 | 21.094% | 0.041 |
| intermediate | Date filter | baseline | Server worker CPU | 2.857 | 2.835–4.48 | 22.197% | 0.022 |
| intermediate | Date filter | optimized | Client elapsed | 1.965 | 1.934–2.891 | 16.119% | 0.031 |
| intermediate | Date filter | optimized | Server worker CPU | 1.672 | 1.648–2.538 | 17.427% | 0.024 |
| intermediate | Aggregation | baseline | Client elapsed | 16.404 | 16.067–21.309 | 12.65% | 0.276 |
| intermediate | Aggregation | baseline | Server worker CPU | 13.192 | 12.681–19.851 | 22.091% | 0.244 |
| intermediate | Aggregation | optimized | Client elapsed | 16.213 | 15.972–19.643 | 7.907% | 0.17 |
| intermediate | Aggregation | optimized | Server worker CPU | 8.602 | 8.562–8.734 | 0.757% | 0.031 |
| broad | Date filter | baseline | Client elapsed | 5.218 | 5.096–5.649 | 3.583% | 0.048 |
| broad | Date filter | baseline | Server worker CPU | 4.754 | 4.687–5.138 | 3.478% | 0.034 |
| broad | Date filter | optimized | Client elapsed | 3.995 | 3.865–4.106 | 1.95% | 0.046 |
| broad | Date filter | optimized | Server worker CPU | 3.478 | 3.431–3.613 | 2.116% | 0.047 |
| broad | Aggregation | baseline | Client elapsed | 36.498 | 36.274–37.008 | 0.715% | 0.158 |
| broad | Aggregation | baseline | Server worker CPU | 21.911 | 21.761–22.02 | 0.439% | 0.074 |
| broad | Aggregation | optimized | Client elapsed | 36.774 | 36.075–40.894 | 4.384% | 0.468 |
| broad | Aggregation | optimized | Server worker CPU | 15.51 | 14.963–15.75 | 1.69% | 0.104 |

## Engineering interpretation

- Large reductions in logical page reads were repeatable within each seven-trial window: values were identical across that window's measured trials. That does **not** mean different datasets or SQL Server versions would behave identically.
- Some client-time medians differed by only tenths of a millisecond and the measured spread can be of similar magnitude. These are observations, **not statistically established gains**.
- Each of the three GitHub CI environments tested a different date-range selectivity. **There are not three independent runs for each exact window**, so differences between runners and selectivity cannot be isolated causally.
- Measurements reflect SQL Server 16.0.4305.5 Developer in ephemeral Linux containers, synthetic orders, cache-warm samples, 4 reported CPUs and ~3,277 MB reported memory. Query plans were captured separately after timing; no plan cache/buffer cache clearing was used.
- The output includes no client or proprietary performance evidence and supports no production performance guarantee.

[Main CPU/IO/plan case study](verified-deep-profile-2026-10-16.md) · [Reproducible methodology](methodology.md).
