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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from psycopg2 import OperationalError
import logging

import openerp
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare, float_round, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.sql import drop_view_if_exists
from openerp import fields, models, api, exceptions, _

_logger = logging.getLogger(__name__)


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
            m.qty = qty

    @api.model
    def _get_orderpoint_date_planned(self, orderpoint, start_date):
        """Returns the date to be set on the procurement made from orderpoint.
        Overridden here to set the date to the needed date."""
        date = datetime.strptime(orderpoint.get_next_need().date, DEFAULT_SERVER_DATETIME_FORMAT)
        return date + relativedelta(seconds=-1)

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        '''
        Create procurement based on Orderpoint

        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        '''
        if use_new_cursor:
            cr = openerp.registry(self.env.cr.dbname).cursor()
            new_env = api.Environment(cr, self.env.user.id, self.env.context)
        else:
            new_env = self.env
        this = self.with_env(new_env)

        orderpoint_env = this.env['stock.warehouse.orderpoint']
        proc_env = this.env['procurement.order']
        dom = company_id and [('company_id', '=', company_id)] or []
        orderpoint_ids = orderpoint_env.search(dom)
        prev_ids = []
        while orderpoint_ids:
            orderpoints = orderpoint_ids[:100]
            orderpoint_ids = orderpoint_ids - orderpoints
            for op in orderpoints:
                try:
                    _logger.debug("Computing orderpoint %s (%s, %s)" % (op.id, op.product_id.name, op.location_id.name))
                    need = op.get_next_need()
                    while need:
                        # We go the the next need (i.e. stock level forecast < minimum qty)
                        next_proc = need.get_next_proc()
                        # We check if there is already a procurement in the future
                        if next_proc:
                            # If there is a future procurement, we reschedule it (required date) to fit our need
                            next_proc.date_planned = this._get_orderpoint_date_planned(op, datetime.today())
                            next_proc.action_reschedule()
                            _logger.debug("Rescheduled proc: %s, (%s, %s)" % (next_proc, next_proc.date_planned,
                                                                                                 next_proc.product_qty))
                        else:
                            # Else, we create a new procurement
                            qty = max(op.product_min_qty, op.product_max_qty) - need.qty
                            reste = op.qty_multiple > 0 and qty % op.qty_multiple or 0.0
                            if float_compare(reste, 0.0, precision_rounding=op.product_uom.rounding) > 0:
                                qty += op.qty_multiple - reste
                            qty = float_round(qty, precision_rounding=op.product_uom.rounding)
                            proc_vals = this._prepare_orderpoint_procurement(op, qty)
                            proc = proc_env.create(proc_vals)
                            proc.check()
                            proc.run()
                            _logger.debug("Created proc: %s, (%s, %s). Product: %s, Location: %s" %
                                          (proc, proc.date_planned, proc.product_qty, op.product_id, op.location_id))
                        need = op.get_next_need()
                except OperationalError:
                    if use_new_cursor:
                        orderpoint_ids = orderpoint_ids | orderpoints
                        new_env.cr.rollback()
                        continue
                    else:
                        raise
            if use_new_cursor:
                new_env.cr.commit()
            if prev_ids == orderpoints:
                break
            else:
                prev_ids = orderpoints
        if use_new_cursor:
            new_env.cr.commit()
            new_env.cr.close()
        return {}


class stock_warehouse_order_point_jit(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.one
    @api.returns('stock.levels.requirements')
    def get_next_need(self):
        """Returns the next stock.level.requirements where the stock level is below minimum qty for the product and
        the location of the orderpoint."""
        need = self.env['stock.levels.requirements'].search([('product_id','=',self.product_id.id),
                                                             ('qty','<',self.product_min_qty),
                                                             ('location_id','=',self.location_id.id),
                                                             ('move_type','=','out')], order='date', limit=1)
        return need


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
    move_type = fields.Selection([('existing','Existing'),('in','Incoming'),('out','Outcoming')],
                                 string="Move type", index=True)
    date = fields.Datetime("Date", index=True)
    qty = fields.Float("Stock quantity", group_operator="last")
    move_qty = fields.Float("Moved quantity")

    def init(self, cr):
        drop_view_if_exists(cr, "stock_levels_report")
        cr.execute("""
        create or replace view stock_levels_report as (
            with recursive top_parent(id, top_parent_id) as (
                    select
                        sl.id, sl.id as top_parent_id
                    from
                        stock_location sl
                        left join stock_location slp on sl.location_id = slp.id
                    where
                        sl.usage='internal' and (sl.location_id is null or slp.usage<>'internal')
                union
                    select
                        sl.id, tp.top_parent_id
                    from
                        stock_location sl, top_parent tp
                    where
                        sl.usage='internal' and sl.location_id=tp.id
            )
            select
                row_number() over () as id,
                foo.product_id,
                pt.categ_id as product_categ_id,
                tp.top_parent_id as location_id,
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
                        sm.date_expected as date,
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
                        sm.date_expected as date,
                        -sm.product_qty as qty
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_id = sl.id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                ) foo
                left join product_product pp on foo.product_id = pp.id
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join top_parent tp on foo.location_id = tp.id
        )
        """)


class stock_levels_requirements(models.Model):
    _name = "stock.levels.requirements"
    _description = "Stock Levels Requirements"
    _order = "date"
    _auto = False

    id = fields.Integer("ID", readonly=True)
    proc_id = fields.Many2one("procurement.order", string="Procurement")
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
        drop_view_if_exists(cr, "stock_levels_requirements")
        cr.execute("""
        create or replace view stock_levels_requirements as (
            with recursive top_parent(id, top_parent_id) as (
                    select
                        sl.id, sl.id as top_parent_id
                    from
                        stock_location sl
                        left join stock_location slp on sl.location_id = slp.id
                    where
                        sl.usage='internal' and (sl.location_id is null or slp.usage<>'internal')
                union
                    select
                        sl.id, tp.top_parent_id
                    from
                        stock_location sl, top_parent tp
                    where
                        sl.usage='internal' and sl.location_id=tp.id
            )
            select
                row_number() over () as id,
                foo.proc_id,
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
                        NULL as proc_id,
                        sq.product_id as product_id,
                        tp.top_parent_id as location_id,
                        NULL as other_location_id,
                        'existing'::text as move_type,
                        max(sq.in_date) as date,
                        sum(sq.qty) as qty
                    from
                        stock_quant sq
                        left join stock_location sl on sq.location_id = sl.id
                        left join top_parent tp on tp.id = sq.location_id
                    where
                        sl.usage = 'internal'::text or sl.usage = 'transit'::text
                    group by sq.product_id, tp.top_parent_id
                union
                    select
                        sm.procurement_id as proc_id,
                        sm.product_id as product_id,
                        tp.top_parent_id as location_id,
                        sm.location_id as other_location_id,
                        'in'::text as move_type,
                        sm.date as date,
                        sm.product_qty as qty
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_dest_id = sl.id
                        left join top_parent tp on tp.id = sm.location_dest_id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union
                    select
                        NULL as proc_id,
                        sm.product_id as product_id,
                        tp.top_parent_id as location_id,
                        sm.location_dest_id as other_location_id,
                        'out'::text as move_type,
                        sm.date as date,
                        -sm.product_qty as qty
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_id = sl.id
                        left join top_parent tp on tp.id = sm.location_id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union
                    select
                        po.id as proc_id,
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
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join top_parent tp on foo.location_id = tp.id
        )
        """)

    @api.one
    @api.returns('procurement.order')
    def get_next_proc(self):
        """Returns the next procurement.order after this line which date is not the line's date."""
        next_line = self.search([('product_id','=',self.product_id.id),('location_id','=',self.location_id.id),
                                 ('date','>',self.date),('proc_id','!=',False)], limit=1)
        return next_line.proc_id
