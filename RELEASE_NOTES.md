# SQL Performance Lab · v0.1.0

Initial public engineering release of an **independent, synthetic** SQL Server optimization laboratory.

## What's included

- Deterministic source-created customers, orders and order lines, installed **only** in a dedicated localhost SQL Server Developer test database.
- Two baseline/candidate T-SQL query studies: date-range access and repeated aggregation.
- Duplicate-aware, full-row semantic validation before benchmark measurements.
- Python CLI for safe seeding, validation and measured benchmarks.
- Automated Python tests and integration tests using a real SQL Server Developer container in GitHub Actions.
- [Permanent raw CI benchmark measurements](https://github.com/Dicureck/sql-performance-lab/blob/main/evidence/ci-benchmark-2026-10-15.json) and [methodology/caveats](https://github.com/Dicureck/sql-performance-lab/blob/main/docs/verified-ci-benchmark-2026-10-15.md).

## Validation

The tagged source is published only after the **SQL Performance Lab CI** workflow succeeds for the exact release commit, including SQL Server integration and smoke benchmark steps.

## Known limitations

Measurements from one ephemeral CI environment are **not** production performance guarantees. Execution plans, logical reads and multiple independently controlled benchmark trials are future research. No customer code, real client records or production database connections are included.

[Install and run](https://github.com/Dicureck/sql-performance-lab#quickstart-local-isolated) · [Changelog](https://github.com/Dicureck/sql-performance-lab/blob/main/CHANGELOG.md)
