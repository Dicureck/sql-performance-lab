"""Offline tests of real plan XML extraction and instrumentation safety."""
import xml.etree.ElementTree as ET
import pytest

from perf_lab.profile import WINDOWS, plan_summary, sql_statement

NS = "http://schemas.microsoft.com/sqlserver/2004/07/showplan"


def test_plan_summary_parses_realistic_sql_server_xml():
    source = f"""<ShowPlanXML xmlns="{NS}" Version="1.6">
      <BatchSequence><Batch><Statements><StmtSimple StatementType="SELECT">
        <QueryPlan><QueryTimeStats CpuTime="7" ElapsedTime="11"/>
          <RelOp PhysicalOp="Index Seek" Parallel="0">
            <RunTimeInformation>
              <RunTimeCountersPerThread Thread="0" ActualRows="6"
               ActualLogicalReads="16" ActualPhysicalReads="0"/>
            </RunTimeInformation>
          </RelOp>
          <RelOp PhysicalOp="Hash Match" Parallel="1">
            <RunTimeInformation><RunTimeCountersPerThread Thread="0"
             ActualRows="6" ActualLogicalReads="0"/></RunTimeInformation>
          </RelOp>
        </QueryPlan>
      </StmtSimple></Statements></Batch></BatchSequence>
    </ShowPlanXML>"""
    info = plan_summary(source)
    assert info["plan_relops"] == 2
    assert info["physical_operators"]["Index Seek"] == 1
    assert info["physical_operators"]["Hash Match"] == 1
    assert info["query_time_cpu_ms"] == 7
    assert info["query_time_elapsed_ms"] == 11
    assert info["actual_runtime_thread_counters"] == 2
    assert info["parallel_relops"] == 1
    assert info["warnings_nodes"] == 0


def test_actual_plan_is_required():
    with pytest.raises(ValueError):
        plan_summary("<Root/>")
    with pytest.raises(ValueError, match="counters"):
        plan_summary(f'<ShowPlanXML xmlns="{NS}"><QueryPlan /></ShowPlanXML>')


def test_profile_sql_writes_only_loopback_only_cases():
    marker = "PL" + "a" * 32 + "_date_filter_baseline"
    statement = sql_statement("date_filter", "baseline", marker)
    assert "lab.orders" in statement
    assert marker in statement
    assert "@StartDate" in statement and "@EndDate" in statement
    with pytest.raises(ValueError, match="marker"):
        sql_statement("date_filter", "baseline", "DROP TABLE x")


def test_windows_are_distinct_and_midnight_aligned():
    assert set(WINDOWS) == {"broad", "focused", "intermediate"}
    assert WINDOWS["focused"] == ("2024-06-01", "2024-06-02")
    assert all(a < b for a, b in WINDOWS.values())
