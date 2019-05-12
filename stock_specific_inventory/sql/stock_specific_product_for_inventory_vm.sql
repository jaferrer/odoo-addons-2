WITH RECURSIVE top_parent(loc_id, top_parent_id) AS (
    SELECT sl.id AS loc_id, sl.id AS top_parent_id
    FROM stock_location sl
    LEFT JOIN stock_location slp ON sl.location_id = slp.id
    WHERE sl.usage = 'internal'
  UNION
    SELECT sl.id AS loc_id, tp.top_parent_id
    FROM stock_location sl, top_parent tp
    WHERE sl.usage = 'internal' AND sl.location_id = tp.loc_id
)
SELECT
  stock_warehouse.id :: TEXT || '-' || product_product.id :: TEXT AS id,
  stock_warehouse.id                                              AS stock_warehouse_id,
  product_product.id                                              AS product_id,
  product_category.name                                           AS category,
  sum(stock_quant.qty)                                            AS qty,
  sum(stock_quant.qty * stock_quant.cost)                         AS value_stock,
  max(stock_inventory.date)                                       AS invetory_date,
  max(stock_move.date)                                            AS move_stock_date
FROM stock_warehouse
  INNER JOIN top_parent ON stock_warehouse.lot_stock_id = top_parent.top_parent_id
  INNER JOIN stock_quant ON stock_quant.location_id = top_parent.loc_id
  INNER JOIN product_product ON product_product.id = stock_quant.product_id
  INNER JOIN product_template ON product_product.product_tmpl_id = product_template.id
  INNER JOIN product_category ON product_template.categ_id = product_category.id
  LEFT JOIN (SELECT
               location_id,
               max(date) AS date
             FROM stock_inventory s
             GROUP BY location_id) stock_inventory ON stock_inventory.location_id = top_parent.loc_id
  LEFT JOIN (SELECT
               location_id,
               product_id,
               max(date) AS date
             FROM stock_move m
             GROUP BY location_id, product_id) stock_move
    ON stock_move.location_id = top_parent.loc_id AND stock_move.product_id = product_product.id
GROUP BY stock_warehouse.id, product_product.id, product_category.name