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

from dateutil.relativedelta import relativedelta
import logging

import openerp.addons.decimal_precision as dp
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler
from openerp.addons.connector.queue.job import job
from openerp.tools import float_compare, float_round, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.sql import drop_view_if_exists
from openerp import fields, models, api

ORDERPOINT_CHUNK = 50

_logger = logging.getLogger(__name__)


@job
def process_orderpoints(session, model_name, ids):
    """Processes the given orderpoints."""
    _logger.info("<<Started chunk of %s orderpoints to process" % ORDERPOINT_CHUNK)
    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as s:
        for op in s.env[model_name].browse(ids):
            op.process()
        s.cr.commit()


class ProcurementOrderQuantity(models.Model):
    _inherit = 'procurement.order'

    qty = fields.Float(string="Quantity", digits_compute=dp.get_precision('Product Unit of Measure'),
                       help='Quantity in the default UoM of the product', compute="_compute_qty", store=True)

    @api.multi
    @api.depends('product_qty', 'product_uom')
    def _compute_qty(self):
        uom_obj = self.env['product.uom']
        for m in self:
            qty = uom_obj._compute_qty_obj(m.product_uom, m.product_qty, m.product_id.uom_id)
            m.qty = qty

    @api.multi
    def reschedule_for_need(self, need):
        """Reschedule procurements to a given need.
        Will set the date of the procurements one second before the date of the need.

        :param need: a 'stock.levels.requirements' record set
        """
        for proc in self:
            new_date = fields.Datetime.from_string(need.date) + relativedelta(seconds=-1)
            proc.date_planned = fields.Datetime.to_string(new_date)
            _logger.debug("Rescheduled proc: %s, new date: %s" % (proc, proc.date_planned))
        self.with_context(reschedule_planned_date=True).action_reschedule()

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        """
        Create procurement based on Orderpoint

        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        """
        orderpoint_env = self.env['stock.warehouse.orderpoint']
        dom = company_id and [('company_id', '=', company_id)] or []
        orderpoint_ids = orderpoint_env.search(dom)
        while orderpoint_ids:
            orderpoints = orderpoint_ids[:ORDERPOINT_CHUNK]
            orderpoint_ids = orderpoint_ids - orderpoints
            process_orderpoints.delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                      orderpoints.ids, description="Computing orderpoints %s" % orderpoints.ids)
        return {}


class StockWarehouseOrderPointJit(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.one
    @api.returns('stock.levels.requirements')
    def get_next_need(self):
        """Returns the next stock.level.requirements where the stock level is below minimum qty for the product and
        the location of the orderpoint."""
        need = self.env['stock.levels.requirements'].search([('product_id', '=', self.product_id.id),
                                                             ('qty', '<', self.product_min_qty),
                                                             ('location_id', '=', self.location_id.id),
                                                             ('move_type', '=', 'out')], order='date', limit=1)
        return need

    @api.multi
    def redistribute_procurements(self, date_start, date_end, days=1):
        """Redistribute procurements related to these orderpoints between date_start and date_end.
        Procurements will be considered as over-supplying if the quantity in stock calculated 'days' after the
        procurement is above the orderpoint calculated maximum quantity. This allows not to consider movements of
        large quantities over a small period of time (that can lead to ponctual over stock) as being over supply.

        This function works by taking procurements one by one from the right. For each it checks whether the quantity
        in stock days after this procurement is above the max value. If it is, the procurement is rescheduled
        temporarily to date_end. This way, we check at which date between the procurement's original date and its
        current date the stock level falls below the minimum quantity and finally place the procurement at this date.

        :param date_start: the starting date as datetime. If False, start at the earliest available date.
        :param date_end: the ending date as datetime
        :param days: defines the number of days after a procurement at which to consider stock quantity.
        """
        for op in self:
            date_domain = [('date_planned', '<', fields.Datetime.to_string(date_end))]
            if date_start:
                date_domain += [('date_planned', '>=', fields.Datetime.to_string(date_start))]
            procs = self.env['procurement.order'].search([('product_id', '=', op.product_id.id),
                                                          ('location_id', '=', op.location_id.id),
                                                          ('state', 'in', ['confirmed', 'running'])]
                                                         + date_domain,
                                                         order="date_planned DESC")
            for proc in procs:
                stock_date = min(
                    fields.Datetime.from_string(proc.date_planned) + relativedelta(days=days),
                    date_end)
                # We check if we have to much of the product in stock days after the procurement
                stock_level = self.env['stock.levels.requirements'].search(
                    [('location_id', '=', proc.location_id.id), ('product_id', '=', proc.product_id.id),
                     ('date', '<', fields.Datetime.to_string(stock_date))],
                    order='date DESC', limit=1)
                if stock_level.qty > op.get_max_qty(stock_date):
                    # We have too much of products: so we reschedule the procurement at end date
                    proc.date_planned = fields.Datetime.to_string(date_end + relativedelta(seconds=-1))
                    proc.with_context(reschedule_planned_date=True).action_reschedule()
                    # Then we reschedule back to the next need if any
                    need = op.get_next_need()
                    if need and fields.Datetime.from_string(need.date) < date_end:
                        # Our rescheduling ended in creating a need before our procurement, so we move it to this date
                        proc.reschedule_for_need(need)
                    _logger.debug("Rescheduled procurement %s, new date: %s" % (proc, proc.date_planned))

    @api.multi
    def create_from_need(self, need):
        """Creates a procurement to fulfill the given need with the data calculated from the given order point.
        Will set the date of the procurement one second before the date of the need.

        :param need: the 'stock.levels.requirements' record set to fulfill
        :param orderpoint: the 'stock.orderpoint' record set with the needed date
        """
        proc_obj = self.env['procurement.order']
        for orderpoint in self:
            qty = max(orderpoint.product_min_qty,
                      orderpoint.get_max_qty(fields.Datetime.from_string(need.date))) - need.qty
            reste = orderpoint.qty_multiple > 0 and qty % orderpoint.qty_multiple or 0.0
            if float_compare(reste, 0.0, precision_rounding=orderpoint.product_uom.rounding) > 0:
                qty += orderpoint.qty_multiple - reste
            qty = float_round(qty, precision_rounding=orderpoint.product_uom.rounding)

            proc_vals = proc_obj._prepare_orderpoint_procurement(orderpoint, qty)
            proc_date = fields.Datetime.from_string(need.date) + relativedelta(seconds=-1)
            proc_vals.update({
                'date_planned': fields.Datetime.to_string(proc_date)
            })
            proc = proc_obj.create(proc_vals)
            proc.run()
            _logger.debug("Created proc: %s, (%s, %s). Product: %s, Location: %s" %
                          (proc, proc.date_planned, proc.product_qty, orderpoint.product_id, orderpoint.location_id))

    @api.multi
    def get_last_scheduled_date(self):
        """Returns the last scheduled date for this order point."""
        self.ensure_one()
        last_schedule = self.env['stock.levels.requirements'].search([('product_id', '=', self.product_id.id),
                                                                      ('location_id', '=', self.location_id.id)],
                                                                     order='date DESC', limit=1)
        res = last_schedule.date and fields.Datetime.from_string(last_schedule.date) or False
        return res

    @api.multi
    def remove_unecessary_procurements(self, timestamp):
        """Remove the unecessary procurements that are placed just before timestamp, and recreate one if necessary to
        match exactly this order point product_min_qty.

        :param timestamp: datetime object
        """
        for orderpoint in self:
            current = self.env['stock.levels.requirements'].search(
                [('product_id', '=', orderpoint.product_id.id), ('location_id', '=', orderpoint.location_id.id),
                 ('date', '>=', fields.Datetime.to_string(timestamp))],
                order='date', limit=1)
            last_outgoing = self.env['stock.levels.requirements'].search(
                [('product_id', '=', orderpoint.product_id.id), ('location_id', '=', orderpoint.location_id.id),
                 ('date', '<=', fields.Datetime.to_string(timestamp)), ('move_type', '=', 'out')],
                order='date DESC', limit=1)
            # We get all procurements placed before timestamp, but after the last outgoing line sorted by inv quantity
            procs = self.env['procurement.order'].search([('product_id', '=', orderpoint.product_id.id),
                                                          ('location_id', '=', orderpoint.location_id.id),
                                                          ('state', 'not in', ['done', 'cancel']),
                                                          ('date_planned', '<=', fields.Datetime.to_string(timestamp)),
                                                          ('date_planned', '>', last_outgoing.date)],
                                                         order='qty DESC')
            _logger.debug("Removing not needed procurements: %s", procs.ids)
            procs.cancel()
            procs.unlink()

    @api.multi
    def process(self):
        """Process this orderpoint."""
        for op in self:
            _logger.debug("Computing orderpoint %s (%s, %s)" % (op.id, op.product_id.name, op.location_id.name))
            need = op.get_next_need()
            date_cursor = False
            while need:
                # We redistribute procurements between date_cursor and need.date
                op.redistribute_procurements(date_cursor, fields.Datetime.from_string(need.date), days=1)
                # We move the date_cursor to the need date
                date_cursor = fields.Datetime.from_string(need.date)
                # We check if there is already a procurement in the future
                next_proc = need.get_next_proc()
                if next_proc:
                    # If there is a future procurement, we reschedule it (required date) to fit our need
                    next_proc.reschedule_for_need(need)
                else:
                    # Else, we create a new procurement
                    op.create_from_need(need)
                need = op.get_next_need()
            # Now we want to make sure that at the end of the scheduled outgoing moves, the stock level is
            # the minimum quantity of the orderpoint.
            last_scheduled_date = op.get_last_scheduled_date()
            if last_scheduled_date:
                date_end = last_scheduled_date + relativedelta(minutes=+1)
                op.redistribute_procurements(date_cursor, date_end)
                op.remove_unecessary_procurements(date_end)


class StockLevelsReport(models.Model):
    _name = "stock.levels.report"
    _description = "Stock Levels Report"
    _order = "date"
    _auto = False

    id = fields.Integer("ID", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", index=True)
    product_categ_id = fields.Many2one("product.category", string="Product Category")
    location_id = fields.Many2one("stock.location", string="Location", index=True)
    other_location_id = fields.Many2one("stock.location", string="Origin/Destination")
    move_type = fields.Selection([('existing', 'Existing'), ('in', 'Incoming'), ('out', 'Outcoming')],
                                 string="Move Type", index=True)
    date = fields.Datetime("Date", index=True)
    qty = fields.Float("Stock Quantity", group_operator="last")
    move_qty = fields.Float("Moved Quantity")

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
                foo.product_id::text || '-'
                    || foo.location_id::text || '-'
                    || coalesce(foo.move_id::text, 'existing') as id,
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
                        sum(sq.qty) as qty,
                        NULL as move_id
                    from
                        stock_quant sq
                        left join stock_location sl on sq.location_id = sl.id
                    where
                        sl.usage = 'internal'::text or sl.usage = 'transit'::text
                    group by sq.product_id, sq.location_id
                union all
                    select
                        sm.product_id as product_id,
                        sm.location_dest_id as location_id,
                        sm.location_id as other_location_id,
                        'in'::text as move_type,
                        sm.date_expected as date,
                        sm.product_qty as qty,
                        sm.id as move_id
                    from
                        stock_move sm
                        left join stock_location sl on sm.location_dest_id = sl.id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union all
                    select
                        sm.product_id as product_id,
                        sm.location_id as location_id,
                        sm.location_dest_id as other_location_id,
                        'out'::text as move_type,
                        sm.date_expected as date,
                        -sm.product_qty as qty,
                        sm.id as move_id
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


class StockLevelsRequirements(models.Model):
    _name = "stock.levels.requirements"
    _description = "Stock Levels Requirements"
    _order = "date"
    _auto = False

    proc_id = fields.Many2one("procurement.order", string="Procurement")
    product_id = fields.Many2one("product.product", string="Product", index=True)
    location_id = fields.Many2one("stock.location", string="Location", index=True)
    move_type = fields.Selection([('existing', 'Existing'), ('in', 'Incoming'), ('out', 'Outcoming'),
                                  ('planned', "Planned (In)")],
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
                foo.product_id::text || '-'
                    || foo.location_id::text || '-'
                    || coalesce(foo.move_id::text, foo.proc_id::text, 'existing') as id,
                foo.proc_id,
                foo.product_id,
                foo.location_id,
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
                        'existing'::text as move_type,
                        least(
                            (select min(date)
                            from
                                stock_move
                            where
                                state::text <> 'cancel'::text
                                and state::text <> 'done'::text
                                and state::text <> 'draft'::text),
                            (select min(po.date_planned)
                            from
                                procurement_order po left join stock_move sm2 on sm2.procurement_id = po.id
                            where
                                po.state::text <> 'cancel'::text
                                and po.state::text <> 'done'::text
                                and (sm2.id is NULL or sm2.state::text = 'draft'::text))
                        ) as date,
                        sum(sq.qty) as qty,
                        NULL as move_id
                    from
                        stock_quant sq
                        left join stock_location sl on sq.location_id = sl.id
                        left join top_parent tp on tp.id = sq.location_id
                    where
                        sl.usage = 'internal'::text or sl.usage = 'transit'::text
                    group by sq.product_id, tp.top_parent_id
                union all
                    select
                        sm.procurement_id as proc_id,
                        sm.product_id as product_id,
                        tp.top_parent_id as location_id,
                        'in'::text as move_type,
                        coalesce(po.date_planned, sm.date) as date,
                        sm.product_qty as qty,
                        sm.id as move_id
                    from
                        stock_move sm
                        left join procurement_order po on sm.procurement_id = po.id
                        left join stock_location sl on sm.location_dest_id = sl.id
                        left join top_parent tp on tp.id = sm.location_dest_id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union all
                    select
                        NULL as proc_id,
                        sm.product_id as product_id,
                        tp.top_parent_id as location_id,
                        'out'::text as move_type,
                        coalesce(po.date_planned, sm.date) as date,
                        -sm.product_qty as qty,
                        sm.id as move_id
                    from
                        stock_move sm
                        left join procurement_order po on sm.procurement_id = po.id
                        left join stock_location sl on sm.location_id = sl.id
                        left join top_parent tp on tp.id = sm.location_id
                    where
                        (sl.usage = 'internal'::text or sl.usage = 'transit'::text)
                        and sm.state::text <> 'cancel'::text
                        and sm.state::text <> 'done'::text
                        and sm.state::text <> 'draft'::text
                union all
                    select
                        po.id as proc_id,
                        po.product_id as product_id,
                        po.location_id as location_id,
                        'planned'::text as move_type,
                        po.date_planned as date,
                        po.qty as qty,
                        NULL as move_id
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
        )
        """)

    @api.one
    @api.returns('procurement.order')
    def get_next_proc(self):
        """Returns the next procurement.order after this line which date is not the line's date."""
        next_line = self.search([('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id),
                                 ('date', '>', self.date), ('proc_id', '!=', False)], limit=1)
        return next_line.proc_id
