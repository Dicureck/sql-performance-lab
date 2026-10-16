#!/usr/bin/env python3
"""Promote verified synthetic SQL profile artifacts into version-controlled evidence.

This script never connects to a database. It rejects incomplete or unexpected
artifacts, validates all three independent CI windows and preserves every
recorded sample and ShowPlan XML. No performance benefit threshold is assumed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

WINDOWS = ("broad", "focused", "intermediate")
CASES = ("date_filter", "report_aggregation")
VARIANTS = ("baseline", "optimized")
SHOWPLAN = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}ShowPlanXML"


def publish(input_dir: Path, destination: Path, run_id: str) -> dict:
    if not run_id.isdecimal():
        raise ValueError("Expected numeric CI run ID")
    if destination.exists():
        raise ValueError("Refusing to overwrite existing immutable CI evidence")
    inventory = {}
    for window in WINDOWS:
        src = input_dir / f"sql-deep-profile-{window}"
        raw = src / "profile.json"
        if not raw.is_file():
            raise ValueError(f"Missing JSON for window {window}")
        doc = json.loads(raw.read_text(encoding="utf-8"))
        if doc.get("window_name") != window or doc.get("iterations") != 7:
            raise ValueError(f"Unexpected window/trial count {window}")
        if doc["environment"].get("synthetic_orders") != 12000:
            raise ValueError("Synthetic order count does not match sealed CI case")
        if set(doc["cases"]) != set(CASES):
            raise ValueError("Synthetic query cases are incomplete")
        files = {}
        for case in CASES:
            case_result = doc["cases"][case]
            verify = case_result["validation"]
            if not verify.get("equivalent") or verify["missing_row_instances"] or verify["extra_row_instances"]:
                raise ValueError(f"Missing/mismatching rows in {window}/{case}")
            for variant in VARIANTS:
                report = case_result[variant]
                if len(report["raw_samples"]) != 7:
                    raise ValueError("Expected seven actual measured SQL trials")
                for sample in report["raw_samples"]:
                    if sample["logical_reads_8kb_pages"] < 0 or sample["worker_cpu_ms"] < 0:
                        raise ValueError("Invalid SQL Server CPU/IO stats")
                filename = f"{case}-{variant}.actual.sqlplan"
                if report["actual_plan_file"] != filename:
                    raise ValueError("Unexpected plan-file reference")
                path = src / filename
                if not path.is_file():
                    raise ValueError(f"Missing actual plan {path}")
                plan = path.read_text(encoding="utf-8")
                if ET.fromstring(plan).tag != SHOWPLAN:
                    raise ValueError("Expected SQL Server ShowPlan XML")
                if "ActualRows" not in plan or "RunTimeCountersPerThread" not in plan:
                    raise ValueError("Plan has no observed execution counters")
                if "SQLLAB_PASSWORD" in plan or "MSSQL_SA_PASSWORD" in plan:
                    raise ValueError("Potential credential field in profile plan")
                files[filename] = path
        inventory[window] = {"profile": raw, "plans": files, "summary": doc}
    destination.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "source_url": f"https://github.com/Dicureck/sql-performance-lab/actions/runs/{run_id}",
        "disclosure": "Independent synthetic GitHub Actions runners; environment-specific observations, not a performance guarantee",
        "windows": {},
    }
    for window, item in inventory.items():
        dest = destination / window
        dest.mkdir()
        shutil.copy2(item["profile"], dest / "profile.json")
        for name, path in item["plans"].items():
            shutil.copy2(path, dest / name)
        manifest["windows"][window] = {
            "file": f"{window}/profile.json",
            "sql_server_version": item["summary"]["environment"]["sql_server_version"],
            "synthetic_dataset": {
                "customers": item["summary"]["environment"]["synthetic_customers"],
                "orders": item["summary"]["environment"]["synthetic_orders"],
                "order_lines": item["summary"]["environment"]["synthetic_order_lines"],
            },
            "cases": {case: {
                "equivalent": item["summary"]["cases"][case]["validation"]["equivalent"],
                "baseline_rows": item["summary"]["cases"][case]["validation"]["baseline_rows"],
                "baseline_logical_reads_median": item["summary"]["cases"][case]["baseline"]["summaries"]["logical_reads_8kb_pages"]["median_ms"],
                "optimized_logical_reads_median": item["summary"]["cases"][case]["optimized"]["summaries"]["logical_reads_8kb_pages"]["median_ms"],
                "baseline_cpu_ms_median": item["summary"]["cases"][case]["baseline"]["summaries"]["worker_cpu_ms"]["median_ms"],
                "optimized_cpu_ms_median": item["summary"]["cases"][case]["optimized"]["summaries"]["worker_cpu_ms"]["median_ms"],
            } for case in CASES},
        }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    manifest = publish(args.input, args.destination, args.run_id)
    print("Archived three independently measured synthetic SQL Server windows:", ", ".join(manifest["windows"]))


if __name__ == "__main__":
    main()
