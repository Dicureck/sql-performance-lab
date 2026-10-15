# Engineering decision record

## ADR-001 — SQL Server-specific rather than pseudo-portable SQL

**Decision:** Target SQL Server 2022 Developer in Docker with native T-SQL, a deliberate date index and SQL Server plan inspection guidance.

**Reason:** Genuine optimization requires a known engine and optimizer. Mixing syntax and index models across SQL dialects would weaken reproducibility.

## ADR-002 — Synthetic schema instead of sanitized customer exports

**Decision:** Generate deterministic fake operational data in SQL. No external CSV downloads and no anonymized customer row samples.

**Reason:** Sanitization can still leak company structure, sensitive rule names, row characteristics or contractual materials. Independently generated data is safer and easier to reproduce.

## ADR-003 — Result multisets, not checksums

**Decision:** Python compares exact `Counter` instances for all row tuples.

**Reason:** `EXCEPT` discards duplicates, and checksums can collide. Multiset equality catches missing and duplicated rows. Cost: full result transfer is part of measured time.

## ADR-004 — SARGable day range

**Decision:** Replace `DATEDIFF` applied to the column with `[start, end)` comparison. CLI accepts `YYYY-MM-DD` only.

**Reason:** This makes a range seek possible. It avoids `BETWEEN` mistakes with fractional seconds. Benefit is workload- and index-dependent.

## ADR-005 — Single aggregate pass

**Decision:** Replace two correlated subqueries with one grouped join across complete orders.

**Reason:** Reduces repeated logical lookups in some execution plans. Important precondition: at least one line per order. SQL Server may optimize both patterns similarly, hence benchmark rather than asserting a speedup.

## ADR-006 — Reversible, local-only setup

**Decision:** `init` can rebuild only one explicitly named local lab database; credentials stay outside version control and Docker binds the host loopback interface.

**Reason:** A public demonstration must be safe to run without accidentally reaching a real customer database.

## ADR-007 — No invented metrics

**Decision:** Benchmark JSON/SVG are generated from live execution and ignored by Git until deliberately reviewed.

**Reason:** Performance improvement claims need measured evidence from a specified environment.
