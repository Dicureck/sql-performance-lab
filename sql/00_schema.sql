/* SQL PERFORMANCE LAB — synthetic schema. Run ONLY in SqlPerformanceLab. */
IF DB_NAME() <> N'SqlPerformanceLab'
    THROW 50001, 'Safety guard: expected SqlPerformanceLab database.', 1;
GO
IF SCHEMA_ID(N'lab') IS NULL EXEC(N'CREATE SCHEMA lab');
GO
DROP TABLE IF EXISTS lab.order_lines;
DROP TABLE IF EXISTS lab.orders;
DROP TABLE IF EXISTS lab.customers;
DROP TABLE IF EXISTS lab.seed_manifest;
GO
CREATE TABLE lab.customers
(
    customer_id INT NOT NULL CONSTRAINT PK_customers PRIMARY KEY CLUSTERED,
    customer_label VARCHAR(32) NOT NULL,
    region_code CHAR(2) NOT NULL,
    segment VARCHAR(16) NOT NULL
);
GO
CREATE TABLE lab.orders
(
    order_id INT NOT NULL CONSTRAINT PK_orders PRIMARY KEY CLUSTERED,
    customer_id INT NOT NULL,
    ordered_at DATETIME2(0) NOT NULL,
    sales_channel VARCHAR(12) NOT NULL,
    order_status CHAR(1) NOT NULL,
    shipping_cents INT NOT NULL,
    CONSTRAINT FK_orders_customers FOREIGN KEY (customer_id)
        REFERENCES lab.customers(customer_id)
);
GO
CREATE TABLE lab.order_lines
(
    order_id INT NOT NULL,
    line_no TINYINT NOT NULL,
    quantity TINYINT NOT NULL,
    unit_price_cents INT NOT NULL,
    CONSTRAINT PK_order_lines PRIMARY KEY CLUSTERED (order_id, line_no),
    CONSTRAINT FK_lines_orders FOREIGN KEY (order_id)
        REFERENCES lab.orders(order_id)
);
GO
CREATE INDEX IX_orders_ordered_at
    ON lab.orders (ordered_at)
    INCLUDE (order_status, sales_channel, shipping_cents, customer_id);
GO
CREATE TABLE lab.seed_manifest
(
    manifest_id TINYINT NOT NULL PRIMARY KEY,
    customer_count INT NOT NULL,
    order_count INT NOT NULL,
    lines_per_order TINYINT NOT NULL,
    seeded_at_utc DATETIME2(0) NOT NULL
);
GO
