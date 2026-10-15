# Contributing

Pull requests that improve correctness checks, deterministic data generation, benchmark rigor, performance-plan documentation or cross-platform developer experience are welcome.

1. Create an issue describing the question being tested.
2. Add baseline and optimized variants under `sql/cases/` using only synthetic datasets.
3. Add exact, multiset-aware integration equivalence tests with at least one edge-case date range.
4. Record methodology without inventing performance numbers.
5. Run `pytest` and optionally the local SQL Server integration test suite.

Do not include proprietary data, customer schema, production credentials or client-specific SQL snippets.
