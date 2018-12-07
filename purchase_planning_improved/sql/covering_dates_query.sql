WITH product_product_restricted AS (
    SELECT *
    FROM product_product pp
    WHERE pp.id IN %s),

    pols_state_order_key AS (
      SELECT
        pol.id AS pol_id,
        pol.product_id,
        pol.date_planned,
        (CASE WHEN po.state IN ('approved', 'except_picking', 'except_invoice')
          THEN 1
         WHEN po.state = 'confirmed'
           THEN 2
         WHEN po.state = 'bid'
           THEN 3
         WHEN po.state = 'sent'
           THEN 4
         WHEN po.state = 'draft'
           THEN 5
         ELSE 6
         END)  AS pol_state_order_key
      FROM purchase_order_line pol
        INNER JOIN product_product_restricted pp ON pp.id = pol.product_id
        INNER JOIN purchase_order po ON pol.order_id = po.id AND po.state NOT IN ('done', 'cancel')),

    pol_converted_uom AS (
      SELECT
        pol.id,
        pol.product_id,
        po.location_id,
        po.id                        AS order_id,
        pol.product_uom,
        key.pol_state_order_key,
        (CASE WHEN pol_unit.id != product_uom.id
          THEN
            round((CASE WHEN pol_unit.uom_type != 'reference'
              THEN 1 / pol_unit.factor
                   ELSE 1 END) *
                  (CASE WHEN product_uom.uom_type != 'reference'
                    THEN product_uom.factor
                   ELSE 1 END) *
                  pol.remaining_qty :: NUMERIC, -log(product_uom.rounding) :: INTEGER)
         ELSE pol.remaining_qty END) AS remaining_po_uom_qty,
        pol.date_planned
      FROM purchase_order_line pol
        INNER JOIN product_product_restricted pp ON pp.id = pol.product_id
        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
        LEFT JOIN purchase_order po ON po.id = pol.order_id
        LEFT JOIN pols_state_order_key key ON key.pol_id = pol.id
        LEFT JOIN product_uom pol_unit ON pol_unit.id = pol.product_uom
        LEFT JOIN product_uom product_uom ON product_uom.id = pt.uom_id
      WHERE pol.remaining_qty > 0 AND po.state NOT IN ('done', 'cancel')
      ORDER BY key.pol_state_order_key, pol.date_planned),

    reception_location_by_product AS (
      SELECT
        pol.product_id,
        po.location_id
      FROM pol_converted_uom pol
        INNER JOIN purchase_order po ON po.id = pol.order_id AND
                                        pol.remaining_po_uom_qty > 0 AND po.state != 'cancel'
      WHERE pol.product_id IS NOT NULL AND po.location_id IS NOT NULL
      GROUP BY pol.product_id, po.location_id
  ),

    pol_converted_uom_with_fake_out_line AS (
    SELECT
      id,
      product_id,
      location_id,
      product_uom,
      pol_state_order_key,
      remaining_po_uom_qty,
      date_planned
    FROM pol_converted_uom

    UNION ALL

    SELECT
      0            AS id,
      rl.product_id,
      rl.location_id,
      pt.uom_id    AS product_uom,
      7            AS pol_state_order_key,
      1            AS remaining_po_uom_qty,
      current_date AS date_planned
    FROM reception_location_by_product rl
      LEFT JOIN product_product pp ON pp.id = rl.product_id
      LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
    GROUP BY rl.product_id, rl.location_id, pt.uom_id),

    quant_reception_quantities AS (
      SELECT
        sq.product_id,
        sq.location_id,
        sum(sq.qty) AS qty
      FROM stock_quant sq
        INNER JOIN reception_location_by_product locs ON locs.product_id = sq.product_id AND
                                                         locs.location_id = sq.location_id
      GROUP BY sq.product_id, sq.location_id
  ),

    moves_out_reception AS (
      SELECT
        sm.date :: DATE,
        sm.product_id,
        sum(sm.product_qty) AS out_qty,
        sm.location_id
      FROM stock_move sm
        INNER JOIN product_product_restricted pp ON pp.id = sm.product_id
        INNER JOIN reception_location_by_product locs ON locs.product_id = sm.product_id AND
                                                         locs.location_id = sm.location_id
      WHERE sm.state NOT IN ('draft', 'done', 'cancel')
      GROUP BY sm.date, sm.product_id, sm.location_id
      ORDER BY sm.date, sm.product_id, sm.location_id),

    global_needs AS (
      SELECT
        move_out.product_id,
        move_out.location_id,
        sum(move_out.out_qty) AS global_need
      FROM moves_out_reception move_out
      GROUP BY move_out.product_id,
        move_out.location_id),

    cumulated_out_qty AS (
      SELECT
        move_out.product_id,
        move_out.location_id,
        move_out.date,
        move_out.out_qty,
        coalesce(sum(moves_before_move.out_qty), 0) AS cumulated_out_qty_with_move
      FROM moves_out_reception move_out
        LEFT JOIN moves_out_reception moves_before_move ON moves_before_move.product_id = move_out.product_id AND
                                                           moves_before_move.location_id = move_out.location_id
                                                           AND moves_before_move.date <= move_out.date
      GROUP BY move_out.product_id,
        move_out.location_id,
        move_out.date,
        move_out.out_qty
      ORDER BY move_out.product_id,
        move_out.location_id,
        move_out.date),

    cumultated_received_qty AS (
      SELECT
        pol.id                                                AS pol_id,
        pol.product_id,
        pol.location_id,
        pol.date_planned,
        pol.pol_state_order_key,
        COALESCE((SELECT sq.qty
                  FROM quant_reception_quantities sq
                  WHERE sq.product_id = pol.product_id AND
                        sq.location_id = pol.location_id), 0) AS stock_qty,
        pol.remaining_po_uom_qty,
        COALESCE((SELECT sum(pols_before_pol.remaining_po_uom_qty)
                  FROM pol_converted_uom_with_fake_out_line pols_before_pol
                  WHERE pols_before_pol.product_id = pol.product_id AND pols_before_pol.location_id = pol.location_id
                        AND (pols_before_pol.pol_state_order_key < pol.pol_state_order_key OR
                             pols_before_pol.pol_state_order_key = pol.pol_state_order_key AND
                             (pols_before_pol.date_planned < pol.date_planned OR
                              (pols_before_pol.date_planned = pol.date_planned AND
                               pols_before_pol.id < pol.id)))),
                 0)                                           AS received_qty_without_pol
      FROM pol_converted_uom_with_fake_out_line pol
      ORDER BY
        pol.pol_state_order_key,
        pol.product_id,
        pol.location_id,
        pol.date_planned
  ),

    real_need_dates AS (
      SELECT
        pol.pol_id,
        pol.pol_state_order_key,
        pol.product_id,
        pol.location_id,
        pol.date_planned,
        pol.stock_qty,
        pol.remaining_po_uom_qty,
        pol.received_qty_without_pol,
        min(move_out.date) AS real_need_date
      FROM cumultated_received_qty pol
        LEFT JOIN cumulated_out_qty move_out
          ON pol.received_qty_without_pol + pol.stock_qty < move_out.cumulated_out_qty_with_move AND
             move_out.product_id = pol.product_id AND
             move_out.location_id = pol.location_id
      GROUP BY pol.pol_id,
        pol.pol_state_order_key,
        pol.product_id,
        pol.location_id,
        pol.date_planned,
        pol.stock_qty,
        pol.remaining_po_uom_qty,
        pol.received_qty_without_pol
      ORDER BY pol.pol_state_order_key,
        pol.product_id,
        pol.location_id,
        pol.date_planned),

    all_dates_with_fake_lines AS (
      SELECT
        rd.*,
        (SELECT min(rd2.real_need_date)
         FROM real_need_dates rd2
         WHERE rd2.product_id = rd.product_id AND rd2.location_id = rd.location_id AND
               rd2.real_need_date > rd.real_need_date) AS covering_date
      FROM real_need_dates rd),

    needed_qties_before_after_pol AS (
      SELECT
        line.*,
        coalesce((SELECT gn.global_need
                  FROM global_needs gn
                  WHERE gn.product_id = line.product_id AND gn.location_id = line.location_id), 0) -
        line.received_qty_without_pol AS total_remaining_need_before_pol,
        coalesce((SELECT gn.global_need
                  FROM global_needs gn
                  WHERE gn.product_id = line.product_id AND gn.location_id = line.location_id), 0) -
        line.received_qty_without_pol -
        line.remaining_po_uom_qty     AS total_remaining_need_after_pol
      FROM all_dates_with_fake_lines line
      WHERE line.pol_id IN (SELECT pol.id
                            FROM purchase_order_line pol)
      ORDER BY line.product_id, line.location_id, line.pol_state_order_key, line.date_planned, line.pol_id)

SELECT
  *,
  (CASE WHEN total_remaining_need_before_pol <= 0.01
    THEN TRUE
   ELSE FALSE END) AS to_delete,
  (CASE WHEN total_remaining_need_after_pol < 0
    THEN (CASE WHEN total_remaining_need_before_pol > 0
      THEN total_remaining_need_before_pol
          ELSE 0 END)
   ELSE 0 END)     AS opmsg_reduce_qty
FROM needed_qties_before_after_pol