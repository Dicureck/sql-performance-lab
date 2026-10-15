from collections import Counter
from pathlib import Path

import pytest

from perf_lab.core import CASES, Config, discrepancy, parse_date, percentile, sql_batches, summarize


def test_sql_batches_split_standalone_go_only():
    sql = "SELECT 'GO';\nGO\nSELECT 2;\n go -- delimiter\nSELECT 3"
    assert sql_batches(sql) == ["SELECT 'GO';", 'SELECT 2;', 'SELECT 3']


def test_counter_preserves_duplicate_multiplicity():
    a = [(1, 'A'), (1, 'A'), (2, 'B')]
    b = [(1, 'A'), (2, 'B'), (2, 'B')]
    verdict = discrepancy(a, b)
    assert not verdict['equivalent']
    assert verdict['missing_row_instances'] == 1
    assert verdict['extra_row_instances'] == 1
    assert discrepancy(a, list(reversed(a)))['equivalent']


def test_percentiles_and_median():
    assert percentile([10, 20, 30], 50) == 20
    assert percentile([10, 20, 30], 95) == pytest.approx(29)
    assert summarize([1, 2, 3])['median_ms'] == 2


def test_dates_restrict_to_calendar_boundaries():
    assert parse_date('2024-03-01') == '2024-03-01'
    for invalid in ('2024-02-30', '2024-04-01 08:00:00', '03/01/2024'):
        with pytest.raises(ValueError):
            parse_date(invalid)


def test_local_only_safety(monkeypatch):
    monkeypatch.setenv('SQLLAB_PASSWORD', 'unit-test-fake')
    monkeypatch.setenv('SQLLAB_DATABASE', 'RealClientDB')
    with pytest.raises(ValueError, match='database'):
        Config.from_env()
    monkeypatch.setenv('SQLLAB_DATABASE', 'SqlPerformanceLab')
    monkeypatch.setenv('SQLLAB_HOST', 'sql.customer.internal')
    with pytest.raises(ValueError, match='loopback'):
        Config.from_env()


def test_case_files_present_and_semantics():
    assert set(CASES) == {'date_filter', 'report_aggregation'}
    for case, folder in CASES.items():
        assert (folder / 'baseline.sql').exists()
        assert (folder / 'optimized.sql').exists()
        for sql in ((folder / 'baseline.sql').read_text(), (folder / 'optimized.sql').read_text()):
            assert '@StartDate' in sql and '@EndDate' in sql
            assert "order_status = 'C'" in sql
    assert 'DATEDIFF(' in (CASES['date_filter'] / 'baseline.sql').read_text()
    assert 'ordered_at >= @StartDate' in (CASES['date_filter'] / 'optimized.sql').read_text()
