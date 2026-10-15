"""Tests against the local synthetic SQL Server only (opt-in)."""
import os
import pytest

from perf_lab.core import CASES, Config, connect, discrepancy, execute_case

pytestmark = pytest.mark.integration


@pytest.fixture(scope='module')
def connection():
    if os.getenv('SQLLAB_INTEGRATION') != '1':
        pytest.skip('Set SQLLAB_INTEGRATION=1 after `python -m perf_lab init`.')
    cn = connect(Config.from_env(), retries=5)
    yield cn
    cn.close()


def test_expected_synthetic_row_counts(connection):
    with connection.cursor() as cur:
        cur.execute('SELECT customer_count, order_count, lines_per_order FROM lab.seed_manifest WHERE manifest_id=1')
        customers, orders, lines_per_order = cur.fetchone()
        for table, expected in [('lab.customers', customers), ('lab.orders', orders),
                                ('lab.order_lines', orders * lines_per_order)]:
            cur.execute(f'SELECT COUNT_BIG(*) FROM {table}')
            assert cur.fetchone()[0] == expected


@pytest.mark.parametrize('case', list(CASES))
@pytest.mark.parametrize('window', [('2024-03-01', '2024-10-01'),
                                    ('2024-01-01', '2025-01-01'),
                                    ('2024-06-01', '2024-06-02')])
def test_full_result_multiset_equivalence(connection, case, window):
    left, _ = execute_case(connection, case, 'baseline', *window)
    right, _ = execute_case(connection, case, 'optimized', *window)
    assert discrepancy(left, right)['equivalent']
