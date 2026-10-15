# Reviewing SQL Server execution plans

1. Start the local SQL Server container and run `python -m perf_lab init`.
2. Open SQL Server Management Studio, Azure Data Studio, or VS Code with a SQL Server connection to `127.0.0.1,14333` and database `SqlPerformanceLab`.
3. Set `@StartDate` and `@EndDate` as `DATETIME2(0)` at whole-calendar-day boundaries:

   ```sql
   DECLARE @StartDate DATETIME2(0) = '2024-03-01T00:00:00';
   DECLARE @EndDate   DATETIME2(0) = '2024-10-01T00:00:00';
   SET STATISTICS IO ON;
   SET STATISTICS TIME ON;
   -- Append one query from sql/cases/<name>/<variant>.sql here.
   ```

4. Enable **Include Actual Execution Plan** where your tool supports it.
5. Record SQL Server product version (`SELECT @@VERSION`), logical reads per table, CPU/elapsed times, index seek/scan, join operators and plan warnings.
6. Explain *why* the measured result behaved as it did. A query that returns fewer rows or drops duplicates is not an optimization.

Do not paste execution plans from a business system here. Use only plans captured from the synthetic lab.
