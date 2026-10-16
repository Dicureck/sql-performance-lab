"""Real SQL Server synthetic performance profiles using query-stats DMVs and actual plans.

Intentionally separate from the old latency CLI. No cache clearing, no client
records, no shared servers. Query stats reflect one tracked SQL statement and
SET STATISTICS XML ON captures plans after timed samples. The CI job is the
only intended authority for published performance observations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import statistics
from time import perf_counter
from uuid import uuid4
import xml.etree.ElementTree as ET

from perf_lab.core import (
    CASES, Config, connect, discrepancy, get_case_query, parse_date, summarize,
)

PLAN_NS = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}"
ROOT = Path(__file__).resolve().parents[2]
WINDOWS = {
    "broad": ("2024-01-01", "2025-01-01"),
    "focused": ("2024-06-01", "2024-06-02"),
    "intermediate": ("2024-03-01", "2024-10-01"),
}
METRIC_SQL = """
SELECT
    qs.execution_count, qs.last_worker_time, qs.last_elapsed_time,
    qs.last_logical_reads, qs.last_physical_reads, qs.last_logical_writes,
    CONVERT(varchar(34), qs.query_hash, 1) AS query_hash,
    CONVERT(varchar(34), qs.query_plan_hash, 1) AS query_plan_hash,
    SUBSTRING(txt.text, (qs.statement_start_offset / 2) + 1,
      ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(txt.text)
         ELSE qs.statement_end_offset END - qs.statement_start_offset) / 2) + 1)
      AS statement_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS txt
WHERE txt.text LIKE %s
ORDER BY qs.last_execution_time DESC;
"""


def sql_statement(case: str, variant: str, marker: str) -> str:
    if not re.fullmatch(r"PL[A-Fa-f0-9]{32}_[a-z_]+_(baseline|optimized)", marker):
        raise ValueError("Unsafe profile marker")
    sql = get_case_query(case, variant)
    return (f"SET NOCOUNT ON;\n"
            "DECLARE @StartDate DATETIME2(0) = CONVERT(DATETIME2(0), %s, 126);\n"
            "DECLARE @EndDate DATETIME2(0) = CONVERT(DATETIME2(0), %s, 126);\n"
            f"/* {marker} */\n{sql}")


def _rows_and_client_time(connection, statement: str, window: tuple[str, str]):
    with connection.cursor() as cursor:
        start = perf_counter()
        cursor.execute(statement, window)
        rows = [tuple(row) for row in cursor.fetchall()]
        duration_ms = (perf_counter() - start) * 1000
    return rows, round(duration_ms, 3)


def _server_stats(connection, marker: str) -> dict:
    with connection.cursor(as_dict=True) as cur:
        # Deliberately excludes this query from the tagged statement match.
        cur.execute(METRIC_SQL, (f"%{marker}%",))
        candidates = cur.fetchall()
    matching = [
        item for item in candidates
        if "SELECT" in item["statement_text"].upper()
        and "lab.orders" in item["statement_text"]
    ]
    if len(matching) != 1:
        raise RuntimeError(
            f"Expected exactly one cached server statement for {marker}; "
            f"found {len(matching)} after filtering {len(candidates)} tagged batch statements; "
            "refusing ungrounded DMV statistics"
        )
    row = matching[0]
    return {
        "execution_count": int(row["execution_count"]),
        "worker_cpu_ms": round(int(row["last_worker_time"]) / 1000, 3),
        "server_elapsed_ms": round(int(row["last_elapsed_time"]) / 1000, 3),
        "logical_reads_8kb_pages": int(row["last_logical_reads"]),
        "physical_reads_8kb_pages": int(row["last_physical_reads"]),
        "logical_writes_8kb_pages": int(row["last_logical_writes"]),
        "query_hash": str(row["query_hash"]),
        "plan_hash": str(row["query_plan_hash"]),
    }


def _extract_plan_xml(connection, statement: str, window: tuple[str, str]) -> str:
    """Actual plan output from SET STATISTICS XML ON; fail if unavailable."""
    with connection.cursor() as cursor:
        cursor.execute("SET STATISTICS XML ON;")
        try:
            cursor.execute(statement, window)
            documents = []
            while True:
                if cursor.description is not None:
                    for row in cursor.fetchall():
                        for value in row:
                            if isinstance(value, (str, bytes)):
                                text = value.decode("utf-8") if isinstance(value, bytes) else value
                                if text.lstrip().startswith("<?xml") or "<ShowPlanXML" in text:
                                    documents.append(text)
                if not cursor.nextset():
                    break
        finally:
            cursor.execute("SET STATISTICS XML OFF;")
    if len(documents) != 1:
        raise RuntimeError(
            f"Expected one actual SQL Server ShowPlan XML result, found {len(documents)}"
        )
    # Parsing guarantees it is genuine ShowPlan XML, not a plain string.
    tree = ET.fromstring(documents[0])
    if tree.tag != PLAN_NS + "ShowPlanXML":
        raise RuntimeError("SQL returned XML, but not a supported SQL Server ShowPlan")
    if tree.find(".//" + PLAN_NS + "RunTimeCountersPerThread") is None:
        raise RuntimeError("No actual execution counters in plan XML")
    return documents[0]


def plan_summary(document: str) -> dict:
    root = ET.fromstring(document)
    if root.tag != PLAN_NS + "ShowPlanXML":
        raise ValueError("Expected SQL Server ShowPlan XML")
    plans = root.findall(".//" + PLAN_NS + "QueryPlan")
    if len(plans) != 1:
        raise ValueError("Expected one SELECT query plan")
    p = plans[0]
    ops = root.findall(".//" + PLAN_NS + "RelOp")
    counters = root.findall(".//" + PLAN_NS + "RunTimeCountersPerThread")
    if not counters:
        raise ValueError("Actual execution counters are absent")
    counts = Counter(op.attrib.get("PhysicalOp", "Unknown") for op in ops)
    warnings = root.findall(".//" + PLAN_NS + "Warnings")
    query_time = p.find(PLAN_NS + "QueryTimeStats")
    return {
        "plan_relops": len(ops),
        "physical_operators": dict(sorted(counts.items())),
        "actual_runtime_thread_counters": len(counters),
        "warnings_nodes": len(warnings),
        "query_time_cpu_ms": (
            int(query_time.attrib["CpuTime"])
            if query_time is not None and "CpuTime" in query_time.attrib else None
        ),
        "query_time_elapsed_ms": (
            int(query_time.attrib["ElapsedTime"])
            if query_time is not None and "ElapsedTime" in query_time.attrib else None
        ),
        "parallel_relops": sum(op.attrib.get("Parallel") == "1" for op in ops),
    }


def collect_case(connection, case: str, window: tuple[str, str],
                 warmups: int, iterations: int, out: Path, token: str) -> dict:
    statements = {
        variant: sql_statement(case, variant, f"PL{token}_{case}_{variant}")
        for variant in ("baseline", "optimized")
    }
    initial = {}
    for variant, statement in statements.items():
        initial[variant], _ = _rows_and_client_time(connection, statement, window)
    verdict = discrepancy(initial["baseline"], initial["optimized"])
    if not verdict["equivalent"]:
        raise RuntimeError(f"{case}: result multiset differs: {verdict}")

    for _ in range(warmups):
        for variant in ("baseline", "optimized"):
            measured_rows, _ = _rows_and_client_time(connection, statements[variant], window)
            if measured_rows != initial[variant]:
                if not discrepancy(initial[variant], measured_rows)["equivalent"]:
                    raise RuntimeError(f"{case}: semantic mismatch during warmup")

    samples = {"baseline": [], "optimized": []}
    # Alternate A/B and B/A, but never mix response time with actual-plan instrumentation.
    for i in range(iterations):
        variants = ("baseline", "optimized") if i % 2 == 0 else ("optimized", "baseline")
        for variant in variants:
            rows, client_ms = _rows_and_client_time(connection, statements[variant], window)
            if not discrepancy(initial[variant], rows)["equivalent"]:
                raise RuntimeError(f"{case}: semantic mismatch during trial {i + 1}")
            metric = _server_stats(
                connection, f"PL{token}_{case}_{variant}"
            )
            samples[variant].append({
                "trial": i + 1, "client_elapsed_ms": client_ms,
                **metric,
            })
    reports = {}
    for variant in ("baseline", "optimized"):
        xml = _extract_plan_xml(connection, statements[variant], window)
        filename = f"{case}-{variant}.actual.sqlplan"
        (out / filename).write_text(xml, encoding="utf-8")
        values = samples[variant]
        reports[variant] = {
            "raw_samples": values,
            "summaries": {
                "client_elapsed_ms": summarize([v["client_elapsed_ms"] for v in values]),
                "worker_cpu_ms": summarize([v["worker_cpu_ms"] for v in values]),
                "server_elapsed_ms": summarize([v["server_elapsed_ms"] for v in values]),
                "logical_reads_8kb_pages": summarize([
                    v["logical_reads_8kb_pages"] for v in values
                ]),
                "physical_reads_8kb_pages": summarize([
                    v["physical_reads_8kb_pages"] for v in values
                ]),
            },
            "actual_plan_file": filename,
            "actual_plan": plan_summary(xml),
        }
    return {"validation": verdict, **reports}


def run(args: argparse.Namespace) -> dict:
    if args.iterations < 3 or args.iterations > 60 or args.warmups < 1 or args.warmups > 20:
        raise ValueError("Require 3..60 iterations and 1..20 warmups")
    if args.window not in WINDOWS:
        raise ValueError("Unknown synthetic date window")
    cfg = Config.from_env()
    token = uuid4().hex
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    start, end = WINDOWS[args.window]
    if parse_date(start) >= parse_date(end):
        raise ValueError("Invalid window")
    result = {
        "lab": "SQL Performance Lab · deeper isolated synthetic profile",
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_name": args.window,
        "window": {"start_inclusive": start, "end_exclusive": end},
        "profile_method": {
            "client_time": "perf_counter around full result fetch",
            "sql_server_cpu": "sys.dm_exec_query_stats.last_worker_time / 1000 (milliseconds)",
            "sql_server_elapsed": "sys.dm_exec_query_stats.last_elapsed_time / 1000 (milliseconds)",
            "logical_reads": "sys.dm_exec_query_stats.last_logical_reads, 8-KB page counts",
            "physical_reads": "sys.dm_exec_query_stats.last_physical_reads, 8-KB page counts",
            "plans": "SET STATISTICS XML ON, actual post-execution plan after measured trials",
            "note": "DMV metrics are scoped to the uniquely tagged executed statement; "
                    "plans recorded separately are not the exact plan instance from each trial. "
                    "No cache clearing or production performance generalization.",
        },
        "environment": {
            "python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "runner": os.environ.get("RUNNER_NAME", "local"),
        },
        "warmups": args.warmups,
        "iterations": args.iterations,
        "cases": {},
    }
    with connect(cfg, retries=10) as cn:
        with cn.cursor() as c:
            c.execute("SELECT CONVERT(varchar(128), SERVERPROPERTY('ProductVersion')), "
                      "CONVERT(varchar(128), SERVERPROPERTY('Edition')), "
                      "CONVERT(varchar(128), SERVERPROPERTY('ProductLevel')), "
                      "CONVERT(varchar(128), SERVERPROPERTY('ProductUpdateLevel')), @@SPID")
            info = c.fetchone()
            c.execute("SELECT customer_count,order_count,lines_per_order FROM lab.seed_manifest "
                      "WHERE manifest_id = 1")
            seeded = c.fetchone()
            if seeded is None:
                raise RuntimeError("No synthetic seed manifest; run init first")
            c.execute("SELECT cpu_count,physical_memory_kb FROM sys.dm_os_sys_info")
            machine = c.fetchone()
        result["environment"].update({
            "sql_server_version": str(info[0]), "edition": str(info[1]),
            "product_level": str(info[2]), "product_update_level": str(info[3]),
            "sql_session_id": int(info[4]), "reported_sql_cpus": int(machine[0]),
            "reported_memory_mb": round(int(machine[1])/1024),
            "synthetic_customers": int(seeded[0]), "synthetic_orders": int(seeded[1]),
            "synthetic_order_lines": int(seeded[1])*int(seeded[2]),
        })
        for case in CASES:
            result["cases"][case] = collect_case(
                cn, case, (start, end), args.warmups, args.iterations, out, token
            )
    (out / "profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("VERIFIED synthetic profile:", args.window,
          "; plan files and observed CPU / logical reads / client durations saved")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", choices=list(WINDOWS), required=True)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--out", default="results/profile")
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
