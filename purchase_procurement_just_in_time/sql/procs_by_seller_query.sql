WITH po_to_process AS (
    SELECT po.id
    FROM procurement_order po
      LEFT JOIN product_product pp ON pp.id = po.product_id
      LEFT JOIN procurement_rule pr ON pr.id = po.rule_id
    WHERE po.state NOT IN ('cancel', 'done', 'exception') AND pr.action = 'buy'),

    min_ps_sequences AS (
      SELECT
        po.id            AS procurement_order_id,
        min(ps.sequence) AS min_ps_sequence
      FROM procurement_order po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
      WHERE po.id IN (SELECT po_to_process.id
                      FROM po_to_process) AND
            (ps.company_id = po.company_id OR ps.company_id IS NULL)
      GROUP BY po.id),

    min_ps_sequences_and_id AS (
      SELECT
        po.id      AS procurement_order_id,
        mps.min_ps_sequence,
        min(ps.id) AS min_ps_id_for_sequence
      FROM procurement_order po
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
        LEFT JOIN min_ps_sequences mps ON mps.procurement_order_id = po.id
      WHERE po.id IN (SELECT po_to_process.id
                      FROM po_to_process) AND
            (ps.company_id = po.company_id OR ps.company_id IS NULL) AND
            ps.sequence = mps.min_ps_sequence
      GROUP BY po.id, mps.min_ps_sequence)

SELECT
  po.id                   AS procurement_order_id,
  (CASE WHEN ps.name IS NOT NULL
    THEN ps.name
   ELSE pp.seller_id END) AS seller_id,
  po.company_id,
  po.location_id,
  po.product_id
FROM procurement_order po
  LEFT JOIN product_product pp ON pp.id = po.product_id
  LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pp.product_tmpl_id
  LEFT JOIN min_ps_sequences_and_id mps ON mps.procurement_order_id = po.id
WHERE po.id IN (SELECT po_to_process.id
                FROM po_to_process) AND
      (ps.company_id = po.company_id OR ps.company_id IS NULL) AND
      ps.sequence = mps.min_ps_sequence AND
      ps.id = mps.min_ps_id_for_sequence