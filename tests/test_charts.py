"""Chart generator must reject fictional/missing or failed performance evidence."""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('chart', ROOT / 'scripts/render_benchmark.py')
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)


def test_reject_unmeasured_result():
    with pytest.raises(ValueError, match='Missing'):
        chart.create_svg({'cases': {}})


def test_reject_failed_semantics():
    with pytest.raises(ValueError, match='failed'):
        chart.create_svg({'cases': {'date_filter': {'validation': {'equivalent': False}}}})


def test_chart_uses_only_passed_in_values():
    fixture = {
        'cases': {
            'date_filter': {
                'validation': {'equivalent': True},
                'baseline': {'median_ms': 10.1},
                'optimized': {'median_ms': 5.2},
            }
        }
    }
    svg = chart.create_svg(fixture)
    assert '10.100 ms' in svg
    assert '5.200 ms' in svg
    assert 'OBSERVED QUERY LATENCY' in svg
