/* CASE 01 / baseline: date calculations on every column value. */
/* @StartDate, @EndDate must be midnight-aligned ISO dates (YYYY-MM-DD). */
SELECT o.sales_channel,
       COUNT_BIG(*) AS completed_orders,
       SUM(CONVERT(BIGINT, o.shipping_cents)) AS shipping_cents
FROM lab.orders AS o
WHERE DATEDIFF(DAY, @StartDate, o.ordered_at) >= 0
  AND DATEDIFF(DAY, @EndDate, o.ordered_at) < 0
  AND o.order_status = 'C'
GROUP BY o.sales_channel;
