# Changelog

This file records verifiable changes to the source project. A package version, change log or draft note does **not** mean that a native GitHub Release or tag has been created.

## [Unreleased] · Evidence improvements

- Verified real SQL Server Developer Edition integration CI and preserved the original synthetic benchmark observations.
- Published [machine-readable raw measurements](evidence/ci-benchmark-2026-10-15.json) copied from the successful CI artifact.
- Explained single-run limitations, complete-row equivalence, SQL Server version and missing plan/read evidence.
- Prepared [release notes draft](RELEASE_NOTES_DRAFT.md) for future publication.

## 0.1.0 · Published source package

- Original safe SQL Server demonstration database, deterministic seeding procedure and two query optimization cases.
- Complete-row multiset checking, benchmark harness and optional chart rendering.
- SQL Server Developer container CI with synthetic fixtures.

**Verification:** [successful CI](https://github.com/Dicureck/sql-performance-lab/actions/runs/38814849103) · [measurement details](docs/verified-ci-benchmark-2026-10-15.md).

**Native GitHub Release:** not yet published by this source file.
