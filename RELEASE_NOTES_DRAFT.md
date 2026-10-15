# Draft Release Notes · SQL Performance Lab v0.1.0

**Status: RELEASE CANDIDATE NOTES — not a GitHub Release or created tag.**

## Scope
- Original synthetic SQL Server customers/orders/lines and safety-checked installation.
- Two baseline-to-candidate T-SQL case studies, both with complete-row multiset validation.
- Python CLI for seeding, correctness checks, benchmarking and optional SVG rendering.
- GitHub Actions SQL Server Developer container integration.
- [Verified CI smoke benchmark](docs/verified-ci-benchmark-2026-10-15.md) with real observed timing on an ephemeral runner.

## Validation
- Successful [CI run](https://github.com/Dicureck/sql-performance-lab/actions/runs/38784723221), including real engine installation and integration tests.
- Evidence artifact `sql-lab-results` retains full raw timings.

## Limitations
CI benchmark timings are **not** production measurements or generalizable optimization guarantees. Query plans and logical reads have not been published as measured CI evidence.

## Release checklist
- [ ] Review current commit, LICENSE and README
- [ ] Tag verified source version
- [ ] Create native GitHub Release through authorized release UI/API
- [ ] Link actual source/CI evidence and changelog
- [ ] Verify assets and release download links
