/* Synthetic and deterministic: no customer, payment, payroll, or client information. */
CREATE OR ALTER PROCEDURE lab.usp_seed_demo
    @CustomerCount INT = 12000,
    @OrderCount INT = 100000,
    @LinesPerOrder TINYINT = 3
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF DB_NAME() <> N'SqlPerformanceLab'
        THROW 50001, 'Safety guard: expected SqlPerformanceLab database.', 1;
    IF @CustomerCount < 10 OR @CustomerCount > 1000000
        THROW 50002, 'CustomerCount must be between 10 and 1000000.', 1;
    IF @OrderCount < 100 OR @OrderCount > 1000000
        THROW 50003, 'OrderCount must be between 100 and 1000000.', 1;
    IF @LinesPerOrder < 1 OR @LinesPerOrder > 5
        THROW 50004, 'LinesPerOrder must be between 1 and 5.', 1;

    BEGIN TRY
        BEGIN TRAN;
        DELETE FROM lab.order_lines;
        DELETE FROM lab.orders;
        DELETE FROM lab.customers;
        DELETE FROM lab.seed_manifest;

        /* Ten digits crossed six times: exact and stable sequence 1..1,000,000. */
        ;WITH D(d) AS (SELECT d FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS x(d)),
        Numbers(n) AS
        (
            SELECT 1 + a.d + 10*b.d + 100*c.d + 1000*d.d + 10000*e.d + 100000*f.d
            FROM D AS a CROSS JOIN D AS b CROSS JOIN D AS c
            CROSS JOIN D AS d CROSS JOIN D AS e CROSS JOIN D AS f
        )
        INSERT INTO lab.customers(customer_id, customer_label, region_code, segment)
        SELECT n, CONCAT('Synthetic Customer ', n),
               CASE n%5 WHEN 0 THEN 'NW' WHEN 1 THEN 'NE' WHEN 2 THEN 'SE'
                            WHEN 3 THEN 'SW' ELSE 'CT' END,
               CASE n%4 WHEN 0 THEN 'Enterprise' WHEN 1 THEN 'SMB'
                            WHEN 2 THEN 'Consumer' ELSE 'Startup' END
        FROM Numbers WHERE n <= @CustomerCount;

        ;WITH D(d) AS (SELECT d FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS x(d)),
        Numbers(n) AS
        (
            SELECT 1 + a.d + 10*b.d + 100*c.d + 1000*d.d + 10000*e.d + 100000*f.d
            FROM D AS a CROSS JOIN D AS b CROSS JOIN D AS c
            CROSS JOIN D AS d CROSS JOIN D AS e CROSS JOIN D AS f
        )
        INSERT INTO lab.orders(order_id, customer_id, ordered_at, sales_channel,
                               order_status, shipping_cents)
        SELECT n,
               1 + (CONVERT(BIGINT, n) * 37 % @CustomerCount),
               DATEADD(MINUTE, CONVERT(INT, (CONVERT(BIGINT, n)*1297)%525600),
                       CONVERT(DATETIME2(0), '2024-01-01T00:00:00', 126)),
               CASE n%4 WHEN 0 THEN 'Web' WHEN 1 THEN 'Mobile'
                            WHEN 2 THEN 'Partner' ELSE 'Retail' END,
               CASE WHEN n%7 IN (0,1) THEN 'X' ELSE 'C' END,
               150 + n%500
        FROM Numbers WHERE n <= @OrderCount;

        /* Each order receives exactly N lines; integer cents avoid floating-point drift. */
        INSERT INTO lab.order_lines(order_id, line_no, quantity, unit_price_cents)
        SELECT o.order_id, CONVERT(TINYINT, v.line_no),
               CONVERT(TINYINT, 1 + (o.order_id + v.line_no)%4),
               500 + (o.order_id*11 + v.line_no*113)%25000
        FROM lab.orders AS o
        CROSS JOIN (VALUES (1),(2),(3),(4),(5)) AS v(line_no)
        WHERE v.line_no <= @LinesPerOrder;

        INSERT INTO lab.seed_manifest
            (manifest_id, customer_count, order_count, lines_per_order, seeded_at_utc)
        VALUES (1, @CustomerCount, @OrderCount, @LinesPerOrder, SYSUTCDATETIME());
        COMMIT TRAN;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        THROW;
    END CATCH;
END;
GO
