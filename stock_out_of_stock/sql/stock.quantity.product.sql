select product_id || '-' || date_stock id,
    date_stock,
    product_id,
    sum(stock_qty) as stock_qty
from stock_quantity 
group by date_stock, product_id