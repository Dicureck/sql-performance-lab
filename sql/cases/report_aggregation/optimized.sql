/* CASE 02 / optimized: one join with a single grouped aggregation. */
/* The synthetic seed guarantees >=1 detail row per order. */
SELECT o.order_id,
       o.customer_id,
       SUM(CONVERT(BIGINT, l.quantity) * l.unit_price_cents) AS gross_cents,
       COUNT_BIG(*) AS line_count
FROM lab.orders AS o
INNER JOIN lab.order_lines AS l ON l.order_id = o.order_id
WHERE o.ordered_at >= @StartDate
  AND o.ordered_at < @EndDate
  AND o.order_status = 'C'
GROUP BY o.order_id, o.customer_id;
