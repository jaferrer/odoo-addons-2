# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import openerp.addons.decimal_precision as dp
from openerp.tools.sql import drop_view_if_exists
from openerp import fields, models, api


class procurement_order_qty(models.Model):
    _inherit = 'procurement.order'

    qty = fields.Float(string="Quantity", digits_compute=dp.get_precision('Product Unit of Measure'),
                       help='Quantity in the default UoM of the product', compute="_compute_qty", store=True)

    @api.multi
    @api.depends('product_qty','product_uom')
    def _compute_qty(self):
        uom_obj = self.env['product.uom']
        for m in self:
            qty = uom_obj._compute_qty_obj(m.product_uom, m.product_qty, m.product_id.uom_id)
            print "Qty: %s, uom: %s, pqty: %s, puom: %s" % (qty, m.product_uom, m.product_qty, m.product_id.uom_id)
            m.qty = qty


class stock_levels_report(models.Model):
    _name = "stock.levels.report"
    _description = "Stock Levels Report"
    _order = "date"
    _auto = False

    id = fields.Integer("ID", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", index=True)
    product_categ_id = fields.Many2one("product.category", string="Product Category")
    location_id = fields.Many2one("stock.location", string="Location", index=True)
    other_location_id = fields.Many2one("stock.location", string="Origin/Destination")
    move_type = fields.Selection([('existing','Existing'),('in','Incoming'),('out','Outcoming'),
                                  ('planned',"Planned (In)")],
                                 string="Move type", index=True)
    date = fields.Datetime("Date", index=True)
    qty = fields.Float("Stock quantity", group_operator="last")
    move_qty = fields.Float("Moved quantity")

    def init(self, cr):
        drop_view_if_exists(cr, "stock_levels_report")
        cr.execute("""
        create or replace view stock_levels_report as (
            select
                row_number() over () as id,
                foo.product_id,
                pt.categ_id as product_categ_id,
                foo.location_id,
                foo.other_location_id,
                foo.move_type,
                sum(foo.qty) over (partition by foo.location_id, foo.product_id order by date) as qty,
                foo.date as date,
                foo.qty as move_qty
            from
                (
                    select
                        sq.product_id as product_id,
                        sq.location_id as location_id,
                        NULL as other_location_id,
                        'existing'::text as move_type,
                        max(sq.in_date) as date,
                        sum(sq.qty) as qty
                    from
                        stock_quant sq
                        left join stock_location sl on sq.location_id = sl.id
                    where
                        sl.usage = 'internal'::text or sl.usage = 'transit'::text
                    group by sq.product_id, sq.location_id
                union
                    select
                        sm.product_id as product_id,
                        sm.location_dest_id as location_id,
                        sm.location_id as other_location_id,
                        'in'::text as move_type,
                        sm.date as date,
                        sm.product_qty as qty
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_dest_id = sl.id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union
                    select
                        sm.product_id as product_id,
                        sm.location_id as location_id,
                        sm.location_dest_id as other_location_id,
                        'out'::text as move_type,
                        sm.date as date,
                        -sm.product_qty as qty
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_id = sl.id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union
                    select
                        po.product_id as product_id,
                        po.location_id as location_id,
                        NULL as other_location_id,
                        'planned'::text as move_type,
                        po.date_planned as date,
                        po.qty as qty
                    from
                        procurement_order po
                        left join stock_location sl on po.location_id = sl.id
                        left join stock_move sm on sm.procurement_id = po.id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and po.state::text <> 'cancel'::text
                        and po.state::text <> 'done'::text
                        and (sm.id is NULL or sm.state::text = 'draft'::text)
                ) foo
                left join product_product pp on foo.product_id = pp.id
                left join product_template pt on pp.product_tmpl_id = pt.id        )
        """)

