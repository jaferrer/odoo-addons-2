select p.id,
    p.id as product_id,
    p.default_code as code,
    '' as owner_id
from product_product p
where p.default_code is not null
union
select cast(spl.product_id as BIGINT) <<16 as id,
    spl.product_id as product_id,
    spl.name as code,
    '' as owner_id
from stock_production_lot spl
where spl.name is not null
union
select cast(spl.product_id as BIGINT) << 32 as id,
    spl.product_id as product_id,
    spl.ref as code,
    '' as owner_id
from stock_production_lot spl
where spl.ref is not null