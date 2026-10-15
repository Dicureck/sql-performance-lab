# SQL case studies — baseline, rewrite, falsifiable hypothesis

## Case 01 — Date predicates and index access

**Question:** Will a half-open range predicate allow a more efficient access path on `lab.orders.ordered_at`?

### Baseline (non-SARGable)

```sql
WHERE DATEDIFF(DAY, @StartDate, o.ordered_at) >= 0
  AND DATEDIFF(DAY, @EndDate,   o.ordered_at) < 0
  AND o.order_status = 'C'
```

Computing `DATEDIFF` for the indexed column often prevents a straightforward index range seek; it can require examining far more rows than the date window selects.

### Optimized

```sql
WHERE o.ordered_at >= @StartDate
  AND o.ordered_at <  @EndDate
  AND o.order_status = 'C'
```

This exposes a seekable range on the index key. The benefit depends on time range selectivity and existing index design; a wide range may legitimately favor a scan.

**Equivalence precondition:** Parameters must denote midnight boundaries. The CLI parses exact `YYYY-MM-DD` and enforces chronological order.

**Expected plans:** Baseline may choose index/clustered scan and predicate; optimized may seek `IX_orders_ordered_at`, but confirm in actual plans rather than treating these as promises.

**Returned fields:** `sales_channel`, `completed_orders`, `shipping_cents`; the harness checks the full multiset.

## Case 02 — Repeated line-item aggregation

**Question:** Is a single grouped join cheaper than computing two independent line-item aggregates for each selected order?

### Baseline (repeated correlated subqueries)

```sql
(SELECT SUM(CONVERT(BIGINT, l.quantity) * l.unit_price_cents)
 FROM lab.order_lines AS l WHERE l.order_id = o.order_id) AS gross_cents,
(SELECT COUNT_BIG(*) FROM lab.order_lines AS l
 WHERE l.order_id = o.order_id) AS line_count
```

### Optimized (single grouped join)

```sql
JOIN lab.order_lines AS l ON l.order_id = o.order_id
...
GROUP BY o.order_id, o.customer_id
```

A single pass computes both `SUM` and `COUNT_BIG`. This may reduce repeated per-order lookups. Optimizer decorrelation and join algorithms can erase the difference or even reverse it.

**Equivalence precondition:** The synthetic dataset guarantees one or more lines per order. For sparse detail data, an `INNER JOIN` would eliminate header-only orders and would not be equivalent. Such a rewrite would require a separate left-join/NULL-handling design and test.

**Returned fields:** `order_id`, `customer_id`, `gross_cents`, `line_count`.

## Neither rewrite is accepted without proof

The harness first checks result cardinality and duplicate-aware full multiset equality; a semantic failure prevents benchmark recording. A benchmark improvement on incorrect output counts as a **failed optimization**.

To record *your own* case-study evidence, run:

```bash
python -m perf_lab benchmark --iterations 15 --warmups 3 --out results/benchmark.json
python scripts/render_benchmark.py results/benchmark.json results/benchmark.svg
```

The [first published CI benchmark evidence](verified-ci-benchmark-2026-10-15.md) comes from a real, temporary SQL Server Developer Edition container using only synthetic records. Plans and logical reads remain future measurements; timing differences from one CI runner must not be generalized.
