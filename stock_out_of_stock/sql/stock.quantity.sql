with product as(
        select pp.id AS product_id,
            pt.id AS product_tmpl_id,
            pt.list_price AS list_price,
            pp.default_code,
            pt.name
        from product_product pp
        inner join product_template pt on pt.id = pp.product_tmpl_id
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
                sl.company_id,
                sl.location_id
         from product p
            inner join stock_quant sq ON sq.product_id = p.product_id
            inner join stock_location sl ON sq.location_id = sl.id
         where sl.usage = 'internal'
         group by p.product_id, sl.company_id, sl.location_id
     ),
    stock_in as (
        SELECT product_id,
            sum(product_uom_qty) qty_recep,
            date(sm.date) date,
            sm.company_id,
            destl.location_id
        FROM stock_move sm
        INNER JOIN stock_location srcl ON sm.location_id = srcl.id
        INNER JOIN stock_location destl ON sm.location_dest_id = destl.id
        WHERE state != 'cancel'
            AND srcl.usage != 'internal'
            AND destl.usage = 'internal'
        GROUP BY product_id, date(sm.date), sm.company_id, destl.location_id
    ),
    stock_out as (
        SELECT product_id,
            sum(product_uom_qty) qty_expe,
            date(sm.date) date,
            sm.company_id,
            srcl.location_id
        FROM stock_move sm
                 INNER JOIN stock_location srcl ON sm.location_id = srcl.id
                 INNER JOIN stock_location destl ON sm.location_dest_id = destl.id
        WHERE state != 'cancel'
          AND srcl.usage = 'internal'
          AND destl.usage != 'internal'
        GROUP BY product_id, date(sm.date), sm.company_id, srcl.location_id
    ),
    stock_change as (
        select coalesce(si.product_id, so.product_id) as product_id,
            coalesce(si.date, so.date) as date,
            coalesce(si.qty_recep,0) - coalesce(so.qty_expe,0) as qty,
            coalesce(si.company_id, so.company_id) as company_id,
            coalesce(si.location_id, so.location_id) as location_id
        from stock_in si
        full outer join stock_out so on si.product_id=so.product_id
            and si.date=so.date
            and si.company_id=so.company_id
            and si.location_id=so.location_id
    ),
    list_date as (
      select date(generate_series('2020-01-01'::timestamp, max(date)::timestamp, '1 days')) as date_stock
      from stock_move
      where state != 'cancel'
    ),
    result as (
        select p.product_id,
            coalesce(sc.qty, 0) stock_change,
            sc.date date_stock_change,
            coalesce(acs.qty,0) + coalesce(sc.qty, 0) stock,
            sc.company_id company_id,
            sum(coalesce(sc.qty, 0)) over (partition by p.product_id, coalesce(sc.location_id, acs.location_id) order by sc.date) as stock_qty,
            lag(sc.date) over (partition by p.product_id, coalesce(sc.location_id, acs.location_id) order by sc.date) as date_min,
            lead(sc.date) over (partition by p.product_id, coalesce(sc.location_id, acs.location_id) order by sc.date) as date_max,
            coalesce(sc.location_id, acs.location_id) as location_id
        from product p
        left join actual_stock acs on p.product_id = acs.product_id
        left join stock_change sc on sc.product_id = p.product_id
            and (acs.location_id=sc.location_id or acs.location_id is null or sc.location_id is null)
    )
select r.product_id || '-' || r.location_id || '-' || ld.date_stock id,
       r.product_id,
       r.stock_change,
       r.stock,
       r.stock_qty,
       r.date_stock_change,
       r.company_id,
       r.location_id,
       ld.date_stock
from list_date ld
left join result r on (ld.date_stock >= r.date_stock_change and ld.date_stock < r.date_max) or (ld.date_stock = r.date_stock_change and r.date_max is null)
where product_id is not null