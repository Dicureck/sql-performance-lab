# Security and disclosure

This repository is a standalone educational sample, not an enterprise database package.

- Run only with a dedicated local `SqlPerformanceLab` database and Docker SQL Server Developer edition.
- `.env` contains local credentials and must never be committed.
- SQL Server port is bound to `127.0.0.1`; the CLI refuses remote database hosts.
- `init` is destructive inside its dedicated lab database. Export anything you want to keep before reseeding.
- No client scripts, external data sources, contracts, private dashboards or actual employee/customer records are permitted.
- Do not open an issue containing credentials or personal records. For security concerns, contact the repository owner through GitHub privately.
