SELECT sml.id AS id,
       sp.id AS picking_id,
       spt.id AS picking_type_id,
       spb.id AS picking_batch_id,
       sml.product_id,
       sml.location_id AS loc_src_id,
       sml.location_dest_id AS loc_desc_id,
       sml.product_qty AS qty_todo,
       sml.owner_id AS owner_id,
       spb.user_id AS user_id,
       spt.tcb_type AS android_type
FROM stock_move_line sml
INNER JOIN stock_picking sp ON sml.picking_id = sp.id
INNER JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
LEFT JOIN stock_picking_batch spb ON sp.batch_id = spb.id
WHERE sp.state = 'assigned'
    AND spt.tcb_type != 'not_managed'