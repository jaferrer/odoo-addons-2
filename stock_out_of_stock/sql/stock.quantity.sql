with product as(
        select pp.id AS product_id,
            pt.id AS product_tmpl_id,
            pt.list_price AS list_price,
            pp.default_code,
            pt.name
        from product_template pt
        inner join product_product pp on pt.id = pp.product_tmpl_id
    ),
    warehouse_company as (
        select sw.id, rc.id
        from stock_warehouse sw
        inner join res_company rc on sw.company_id = rc.id
        group by rc.id, sw.id
    ),
     actual_stock AS (
         select p.product_id as product_id,
            sum(sq.quantity) qty,
                sl.company_id
         from product p
            inner join stock_quant sq ON sq.product_id = p.product_id
            inner join stock_location sl ON sq.location_id = sl.id
         where sl.usage = 'internal'
         group by p.product_id, sl.company_id
     ),
    stock_in as (
        SELECT product_id,
            sum(product_uom_qty) qty_recep,
            date(sm.date) date,
            sm.company_id
        FROM stock_move sm
        INNER JOIN stock_location srcl ON sm.location_id = srcl.id
        INNER JOIN stock_location destl ON sm.location_dest_id = destl.id
        WHERE state != 'cancel'
            AND srcl.usage != 'internal'
            AND destl.usage = 'internal'
        GROUP BY product_id, date(sm.date), sm.company_id
    ),
    stock_out as (
        SELECT product_id,
            sum(product_uom_qty) qty_expe,
            date(sm.date) date,
            sm.company_id
        FROM stock_move sm
                 INNER JOIN stock_location srcl ON sm.location_id = srcl.id
                 INNER JOIN stock_location destl ON sm.location_dest_id = destl.id
        WHERE state != 'cancel'
          AND srcl.usage = 'internal'
          AND destl.usage != 'internal'
        GROUP BY product_id, date(sm.date), sm.company_id
    ),
    stock_change as (
        select coalesce(si.product_id, so.product_id) as product_id,
            coalesce(si.date, so.date) as date,
            coalesce(si.qty_recep,0) - coalesce(so.qty_expe,0) as qty,
            coalesce(si.company_id, so.company_id) as company_id
        from stock_in si
        full outer join stock_out so on si.product_id=so.product_id
            and si.date=so.date
            and si.company_id=so.company_id
    ),
    result as (
        select p.product_id,
            p.default_code,
            p.name,
            acs.qty qty,
            coalesce(sc.qty, 0) stock_change,
            sc.date date_stock_change,
            coalesce(acs.qty,0) + coalesce(sc.qty, 0) stock,
            sc.company_id company_id
        from product p
        left join actual_stock acs on p.product_id = acs.product_id
        left join stock_change sc on sc.product_id = p.product_id
    )
select product_id,
    name,
    stock_change,
    date_stock_change,
    company_id
from result