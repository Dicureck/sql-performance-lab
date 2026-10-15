"""Safe local connection, statement loading, result equivalence, and timing."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from time import perf_counter, sleep
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # enables pure-Python static tests without an installed server
    pass

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'date_filter': ROOT / 'sql/cases/date_filter',
    'report_aggregation': ROOT / 'sql/cases/report_aggregation',
}
DATABASE = 'SqlPerformanceLab'
ALLOWED_HOSTS = {'127.0.0.1', 'localhost', '::1'}


@dataclass(frozen=True)
class Config:
    host: str = '127.0.0.1'
    port: int = 14333
    user: str = 'sa'
    password: str = ''
    database: str = DATABASE

    @classmethod
    def from_env(cls) -> 'Config':
        cfg = cls(
            host=os.getenv('SQLLAB_HOST', '127.0.0.1'),
            port=int(os.getenv('SQLLAB_PORT', '14333')),
            user=os.getenv('SQLLAB_USER', 'sa'),
            password=os.getenv('SQLLAB_PASSWORD', ''),
            database=os.getenv('SQLLAB_DATABASE', DATABASE),
        )
        if cfg.host.lower() not in ALLOWED_HOSTS:
            raise ValueError('Safety guard: lab only allows loopback database hosts.')
        if cfg.database != DATABASE:
            raise ValueError(f'Safety guard: database must be {DATABASE}.')
        if not cfg.password:
            raise ValueError('Missing SQLLAB_PASSWORD; copy .env.example to .env first.')
        return cfg


def connect(cfg: Config, database: str | None = None, retries: int = 1):
    """Create connection; transient startup failures are retried."""
    import pymssql
    last_error = None
    for attempt in range(retries):
        try:
            return pymssql.connect(
                server=cfg.host, port=cfg.port, user=cfg.user,
                password=cfg.password, database=database or cfg.database,
                autocommit=True, login_timeout=4, timeout=90,
            )
        except pymssql.Error as err:
            last_error = err
            if attempt < retries - 1:
                sleep(3)
    raise RuntimeError(f'SQL Server not available on {cfg.host}:{cfg.port}; is Docker running?') from last_error


def sql_batches(script: str) -> list[str]:
    """Split on standalone GO lines (not a fully general T-SQL lexer)."""
    return [s.strip() for s in re.split(r'^\s*GO\s*(?:--[^\n]*)?$', script,
                                              flags=re.MULTILINE | re.IGNORECASE) if s.strip()]


def execute_file(connection, relative_path: str):
    source = (ROOT / relative_path).read_text(encoding='utf-8')
    cursor = connection.cursor()
    for batch in sql_batches(source):
        cursor.execute(batch)
        # Consume driver-generated results before continuing to the next batch.
        while cursor.nextset():
            pass
    cursor.close()


def get_case_query(case: str, variant: str) -> str:
    if case not in CASES or variant not in {'baseline', 'optimized'}:
        raise ValueError('Unknown benchmark case or variant.')
    return (CASES[case] / (variant + '.sql')).read_text(encoding='utf-8')


def execute_case(connection, case: str, variant: str, start_date: str, end_date: str):
    statement = '''SET NOCOUNT ON;
DECLARE @StartDate DATETIME2(0) = CONVERT(DATETIME2(0), %s, 126);
DECLARE @EndDate DATETIME2(0) = CONVERT(DATETIME2(0), %s, 126);
''' + get_case_query(case, variant)
    with connection.cursor() as cursor:
        started = perf_counter()
        cursor.execute(statement, (start_date, end_date))
        rows = [tuple(row) for row in cursor.fetchall()]
        elapsed_ms = (perf_counter() - started) * 1000
    return rows, elapsed_ms


def discrepancy(left: list[tuple], right: list[tuple]) -> dict:
    """Compare full row *multisets*: EXCEPT alone loses duplicate multiplicity."""
    left_counts, right_counts = Counter(left), Counter(right)
    missing = left_counts - right_counts
    extra = right_counts - left_counts
    return {
        'equivalent': not missing and not extra,
        'baseline_rows': len(left),
        'optimized_rows': len(right),
        'missing_row_instances': sum(missing.values()),
        'extra_row_instances': sum(extra.values()),
        'distinct_baseline_rows': len(left_counts),
        'distinct_optimized_rows': len(right_counts),
    }


def percentile(values: list[float], percentage: float) -> float:
    if not values:
        raise ValueError('No values supplied.')
    vals = sorted(values)
    loc = (len(vals) - 1) * percentage / 100
    lo = int(loc)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (loc - lo)


def summarize(values: list[float]) -> dict:
    return {'runs': len(values), 'median_ms': round(median(values), 3),
            'p95_ms': round(percentile(values, 95), 3),
            'min_ms': round(min(values), 3), 'max_ms': round(max(values), 3)}


def parse_date(text: str) -> str:
    """Require midnight-aligned dates so baseline DATEDIFF matches half-open range."""
    try:
        return datetime.strptime(text, '%Y-%m-%d').date().isoformat()
    except ValueError as err:
        raise ValueError('Dates must use YYYY-MM-DD, at midnight boundaries.') from err
