"""Command-line harness for SQL Server 2022 local demonstration."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

from perf_lab.core import (
    CASES, Config, connect, discrepancy, execute_case, execute_file,
    parse_date, summarize,
)


def initialize(args, cfg):
    """Create the *dedicated* lab database then replace only its synthetic tables."""
    with connect(cfg, database='master', retries=20) as master:
        with master.cursor() as c:
            c.execute("IF DB_ID(N'SqlPerformanceLab') IS NULL CREATE DATABASE SqlPerformanceLab")
    with connect(cfg, retries=20) as cn:
        execute_file(cn, 'sql/00_schema.sql')
        execute_file(cn, 'sql/01_seed.sql')
        with cn.cursor() as c:
            c.execute('EXEC lab.usp_seed_demo @CustomerCount=%s, @OrderCount=%s, @LinesPerOrder=%s',
                      (args.customers, args.orders, args.lines_per_order))
            c.execute('SELECT COUNT_BIG(*) FROM lab.customers')
            n_customers = c.fetchone()[0]
            c.execute('SELECT COUNT_BIG(*) FROM lab.orders')
            n_orders = c.fetchone()[0]
            c.execute('SELECT COUNT_BIG(*) FROM lab.order_lines')
            n_lines = c.fetchone()[0]
    if (n_customers, n_orders, n_lines) != (
        args.customers, args.orders, args.orders * args.lines_per_order
    ):
        raise RuntimeError('Seed row-count invariant failed.')
    print(f'Synthetic seed complete: {n_customers:,} customers, {n_orders:,} orders, {n_lines:,} lines.')


def run_suite(args, cfg):
    start_date, end_date = parse_date(args.start_date), parse_date(args.end_date)
    if start_date >= end_date:
        raise ValueError('Start date must precede end date.')
    if args.iterations < 1 or args.iterations > 100 or args.warmups < 0 or args.warmups > 20:
        raise ValueError('Iterations must be 1..100 and warmups 0..20.')

    result = {
        'lab': 'SQL Performance Lab',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'execution_environment': {
            'python': platform.python_version(), 'system': platform.system(),
            'machine': platform.machine(),
            'database_engine': 'Microsoft SQL Server (local container)',
            'measurement': 'client wall-clock elapsed time including result transfer',
        },
        'window': {'start_inclusive': start_date, 'end_exclusive': end_date},
        'warmup_runs_per_variant': args.warmups,
        'measured_runs_per_variant': args.iterations,
        'cases': {},
    }
    with connect(cfg, retries=5) as cn:
        with cn.cursor() as c:
            c.execute('SELECT customer_count, order_count, lines_per_order FROM lab.seed_manifest WHERE manifest_id = 1')
            manifest = c.fetchone()
            c.execute("SELECT CONVERT(VARCHAR(128), SERVERPROPERTY('ProductVersion')), CONVERT(VARCHAR(128), SERVERPROPERTY('Edition'))")
            engine_version, engine_edition = c.fetchone()
        if not manifest:
            raise RuntimeError('Missing seed manifest; run `init` first.')
        result['execution_environment']['sql_server_version'] = engine_version
        result['execution_environment']['sql_server_edition'] = engine_edition
        result['synthetic_dataset'] = {
            'customers': int(manifest[0]), 'orders': int(manifest[1]),
            'order_lines': int(manifest[1]) * int(manifest[2]),
        }
        for case in CASES:
            baselines, optimized, samples = [], [], {}
            for variant in ('baseline', 'optimized'):
                rows, _ = execute_case(cn, case, variant, start_date, end_date)
                samples[variant] = rows
            diff = discrepancy(samples['baseline'], samples['optimized'])
            if not diff['equivalent']:
                raise RuntimeError(f'Validation FAILED for {case}: {diff}')
            for _ in range(args.warmups):
                execute_case(cn, case, 'baseline', start_date, end_date)
                execute_case(cn, case, 'optimized', start_date, end_date)
            # A/B vs B/A alternation counters systematic warm cache ordering.
            for i in range(args.iterations):
                order = ('baseline', 'optimized') if i % 2 == 0 else ('optimized', 'baseline')
                for variant in order:
                    _, ms = execute_case(cn, case, variant, start_date, end_date)
                    (baselines if variant == 'baseline' else optimized).append(ms)
            before, after = summarize(baselines), summarize(optimized)
            ratio = before['median_ms'] / after['median_ms'] if after['median_ms'] else None
            result['cases'][case] = {
                'validation': diff,
                'baseline': before, 'optimized': after,
                'speedup_ratio': round(ratio, 3) if ratio is not None else None,
                'percent_reduction': round(100*(1-after['median_ms']/before['median_ms']), 2)
                                     if before['median_ms'] else None,
                'raw_ms': {'baseline': [round(x, 3) for x in baselines],
                           'optimized': [round(x, 3) for x in optimized]},
            }
            print(f'PASS {case}: {diff["baseline_rows"]:,} matching rows | '
                  f'median {before["median_ms"]:.1f}ms -> {after["median_ms"]:.1f}ms '
                  f'({ratio:.2f}x)' if ratio is not None else f'PASS {case}')
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f'Results saved: {output}')
    return result


def build_parser():
    parser = argparse.ArgumentParser(description='Local-only synthetic SQL Server optimization lab')
    subs = parser.add_subparsers(dest='command', required=True)
    init = subs.add_parser('init', help='RESET and seed the dedicated SqlPerformanceLab database')
    init.add_argument('--customers', type=int, default=12000)
    init.add_argument('--orders', type=int, default=100000)
    init.add_argument('--lines-per-order', type=int, default=3)
    for command in ('validate', 'benchmark'):
        p = subs.add_parser(command, help=f'Run semantic equivalence checks and {command}')
        p.add_argument('--start-date', default='2024-03-01')
        p.add_argument('--end-date', default='2024-10-01')
        p.add_argument('--warmups', type=int, default=1 if command == 'validate' else 2)
        p.add_argument('--iterations', type=int, default=1 if command == 'validate' else 7)
        p.add_argument('--out', default='' if command == 'validate' else 'results/benchmark.json')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        cfg = Config.from_env()
        if args.command == 'init':
            initialize(args, cfg)
        else:
            run_suite(args, cfg)
    except (ValueError, RuntimeError) as err:
        print(f'ERROR: {err}', file=sys.stderr)
        raise SystemExit(1) from err


if __name__ == '__main__':
    main()
