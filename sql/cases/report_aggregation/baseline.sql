/* CASE 02 / baseline: two scalar subqueries repeat lookups per order. */
SELECT o.order_id,
       o.customer_id,
       (SELECT SUM(CONVERT(BIGINT, l.quantity) * l.unit_price_cents)
        FROM lab.order_lines AS l WHERE l.order_id = o.order_id) AS gross_cents,
       (SELECT COUNT_BIG(*) FROM lab.order_lines AS l
        WHERE l.order_id = o.order_id) AS line_count
FROM lab.orders AS o
WHERE o.ordered_at >= @StartDate
  AND o.ordered_at < @EndDate
  AND o.order_status = 'C';
