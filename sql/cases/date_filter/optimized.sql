/* CASE 01 / optimized: half-open range enables ordered_at index seeks. */
SELECT o.sales_channel,
       COUNT_BIG(*) AS completed_orders,
       SUM(CONVERT(BIGINT, o.shipping_cents)) AS shipping_cents
FROM lab.orders AS o
WHERE o.ordered_at >= @StartDate
  AND o.ordered_at < @EndDate
  AND o.order_status = 'C'
GROUP BY o.sales_channel;
