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
from openerp.tools import float_compare, float_round
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
        s.commit()


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
        :param need: dict
        """
        for proc in self:
            new_date = fields.Datetime.from_string(need['date']) + relativedelta(seconds=-1)
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
        if self.env.context.get('compute_product_ids') and not self.env.context.get('compute_all_products'):
            dom += [('product_id', 'in', self.env.context.get('compute_product_ids'))]
        orderpoint_ids = orderpoint_env.search(dom)
        while orderpoint_ids:
            orderpoints = orderpoint_ids[:ORDERPOINT_CHUNK]
            orderpoint_ids = orderpoint_ids - orderpoints
            if self.env.context.get('without_job'):
                for op in orderpoints:
                    op.process()
            else:
                process_orderpoints.delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                          orderpoints.ids, description="Computing orderpoints %s" % orderpoints.ids)
        return {}


class StockWarehouseOrderPointJit(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.multi
    @api.returns('procurement.order')
    def get_next_proc(self, need):
        """Returns the next procurement.order after this line which date is not the line's date."""
        self.ensure_one()
        next_line = self.compute_stock_levels_requirements(product_id=self.product_id.id,
                                                           location_id=self.location_id.id,
                                                           list_move_types=('existing', 'in', 'out', 'planned',),
                                                           limit=False, parameter_to_sort='date', to_reverse=False)
        next_line = [x for x in next_line if x.get('date') and x['date'] > need['date'] and x['proc_id']]
        if next_line:
            return self.env['procurement.order'].search([('id', '=', next_line[0]['proc_id'])])
        return self.env['procurement.order']

    @api.multi
    def get_next_need(self):
        """Returns a dict of stock level requirements where the stock level is below minimum qty for the product and
        the location of the orderpoint."""
        self.ensure_one()
        need = self.compute_stock_levels_requirements(product_id=self.product_id.id, location_id=self.location_id.id,
                                                      list_move_types=('out',), limit=False, parameter_to_sort='date',
                                                      to_reverse=False)
        need = [x for x in need if x['qty'] < self.product_min_qty]
        if need:
            need = need[0]
            if need.get('id') or need.get('proc_id') or need.get('product_id') or need.get('location_id') or \
                    need.get('move_type') or need.get('qty') or need.get('date') or need.get('move_qty'):
                return need
        return False

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
                                                          ('state', 'in', ['confirmed', 'running', 'exception'])]
                                                         + date_domain,
                                                         order="date_planned DESC")
            for proc in procs:
                stock_date = min(
                    fields.Datetime.from_string(proc.date_planned) + relativedelta(days=days),
                    date_end)
                stock_level = self.env['stock.warehouse.orderpoint'].compute_stock_levels_requirements(
                                                        product_id=proc.product_id.id, location_id=proc.location_id.id,
                                                        list_move_types=('in', 'out', 'existing', 'planned',),
                                                        parameter_to_sort='date', to_reverse=True, limit=False)
                stock_level = [x for x in stock_level if x.get('date') and x['date'] <
                               fields.Datetime.to_string(stock_date)]
                if stock_level and stock_level[0]['qty'] > op.get_max_qty(stock_date):
                    # We have too much of products: so we reschedule the procurement at end date
                    proc.date_planned = fields.Datetime.to_string(date_end + relativedelta(seconds=-1))
                    proc.with_context(reschedule_planned_date=True).action_reschedule()
                    # Then we reschedule back to the next need if any
                    need = op.get_next_need()
                    if need and fields.Datetime.from_string(need['date']) < date_end:
                        # Our rescheduling ended in creating a need before our procurement, so we move it to this date
                        proc.reschedule_for_need(need)
                    _logger.debug("Rescheduled procurement %s, new date: %s" % (proc, proc.date_planned))

    @api.multi
    def create_from_need(self, need):
        """Creates a procurement to fulfill the given need with the data calculated from the given order point.
        Will set the date of the procurement one second before the date of the need.

        :param need: the 'stock levels requirements' dictionary to fulfill
        :param orderpoint: the 'stock.orderpoint' record set with the needed date
        """
        proc_obj = self.env['procurement.order']
        for orderpoint in self:
            qty = max(orderpoint.product_min_qty,
                      orderpoint.get_max_qty(fields.Datetime.from_string(need['date']))) - need['qty']
            reste = orderpoint.qty_multiple > 0 and qty % orderpoint.qty_multiple or 0.0
            if float_compare(reste, 0.0, precision_rounding=orderpoint.product_uom.rounding) > 0:
                qty += orderpoint.qty_multiple - reste
            qty = float_round(qty, precision_rounding=orderpoint.product_uom.rounding)

            proc_vals = proc_obj._prepare_orderpoint_procurement(orderpoint, qty)
            proc_date = fields.Datetime.from_string(need['date']) + relativedelta(seconds=-1)
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
        last_schedule = self.env['stock.warehouse.orderpoint'].compute_stock_levels_requirements(
                                                                product_id=self.product_id.id,
                                                                location_id=self.location_id.id,
                                                                list_move_types=['in', 'out', 'existing'], limit=1,
                                                                parameter_to_sort='date', to_reverse=True)
        res = last_schedule and last_schedule[0].get('date') and \
              fields.Datetime.from_string(last_schedule[0].get('date')) or False
        return res

    @api.multi
    def remove_unecessary_procurements(self, timestamp):
        """Remove the unecessary procurements that are placed just before timestamp, and recreate one if necessary to
        match exactly this order point product_min_qty.

        :param timestamp: datetime object
        """
        for orderpoint in self:
            last_outgoing = self.env['stock.warehouse.orderpoint'].compute_stock_levels_requirements(
                product_id=orderpoint.product_id.id, location_id=orderpoint.location_id.id,
                list_move_types=('out',), limit=1, parameter_to_sort='date', to_reverse=True
            )
            last_outgoing = [x for x in last_outgoing if x['date'] <= fields.Datetime.to_string(timestamp)]
            # We get all procurements placed before timestamp, but after the last outgoing line sorted by inv quantity
            procs = self.env['procurement.order'].search([('product_id', '=', orderpoint.product_id.id),
                                                          ('location_id', '=', orderpoint.location_id.id),
                                                          ('state', 'not in', ['done', 'cancel']),
                                                          ('date_planned', '<=', fields.Datetime.to_string(timestamp))],
                                                         order='qty DESC')
            if last_outgoing:
                procs = procs.filtered(lambda x: x.date_planned > last_outgoing[0]['date'])
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
                op.redistribute_procurements(date_cursor, fields.Datetime.from_string(need['date']), days=1)
                # We move the date_cursor to the need date
                date_cursor = fields.Datetime.from_string(need['date'])
                # We check if there is already a procurement in the future
                next_proc = op.get_next_proc(need)
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

    @api.model
    def compute_stock_levels_requirements(self, product_id, location_id, list_move_types, limit=1,
                                          parameter_to_sort='date', to_reverse=False):

        """
        Computes stock level report
        :param product_id: int
        :param location_id: int
        :param list_move_types: tuple or list of strings (move types)
        :param limit: maximum number of lines in the result
        :param parameter_to_sort: str
        :param to_reverse: bool
        :return: list of need dictionaries
        """

        # Computing the top parent location
        min_date = False
        result = []
        intermediate_result = []
        stock_move_restricted_in = self.env['stock.move'].search([('product_id', '=', product_id),
                                                                  ('state', 'not in', ['cancel', 'done', 'draft']),
                                                                  ('location_dest_id', 'child_of', location_id)],
                                                                 order='date')
        stock_move_restricted_out = self.env['stock.move'].search([('product_id', '=', product_id),
                                                                   ('state', 'not in', ['cancel', 'done', 'draft']),
                                                                   ('location_id', 'child_of', location_id)],
                                                                  order='date')
        stock_quant_restricted = self.env['stock.quant'].search([('product_id', '=', product_id),
                                                                 ('location_id', 'child_of', location_id)])
        procurement_order_restricted = self.env['procurement.order'].search([('product_id', '=', product_id),
                                                                             ('location_id', 'child_of', location_id),
                                                                             ('state', 'not in', ['cancel','done'])
                                                                             ], order='date_planned')
        dates = []
        if stock_move_restricted_in:
            dates += [stock_move_restricted_in[0].date]
        if stock_move_restricted_out:
            dates += [stock_move_restricted_out[0].date]
        procurement_order_restricted = procurement_order_restricted.filtered(
            lambda p: not p.move_ids or any([(m.state == 'draft') for m in p.move_ids])
        )
        if procurement_order_restricted:
            dates += [procurement_order_restricted[0].date_planned]
        if dates:
            min_date = min(dates)

        # existing items
        existing_qty = sum([x.qty for x in stock_quant_restricted])
        intermediate_result += [{
            'proc_id': False,
            'location_id': location_id,
            'move_type': 'existing',
            'date': min_date,
            'qty': existing_qty,
            'move_id': False,
        }]

        # incoming items
        for sm in stock_move_restricted_in:
            procurement = sm.procurement_id
            date = False
            if procurement and procurement.date_planned:
                date = procurement.date_planned
            elif sm.date:
                date = sm.date
            intermediate_result += [{
                    'proc_id': procurement.id,
                    'location_id': location_id,
                    'move_type': 'in',
                    'date': date,
                    'qty': sm.product_qty,
                    'move_id': sm.id,
                }]

        # outgoing items
        for sm in stock_move_restricted_out:
            procurement = sm.procurement_id
            date = False
            if procurement and procurement.date_planned:
                date = procurement.date_planned
            elif sm.date:
                date = sm.date
            intermediate_result += [{
                    'proc_id': False,
                    'location_id': location_id,
                    'move_type': 'out',
                    'date': date,
                    'qty': - sm.product_qty,
                    'move_id': sm.id,
                }]

        # planned items
        for po in procurement_order_restricted:
            intermediate_result += [{
                    'proc_id': po.id,
                    'location_id': location_id,
                    'move_type': 'planned',
                    'date': po.date_planned,
                    'qty': po.qty,
                    'move_id': False,
                }]

        intermediate_result = sorted(intermediate_result, key=lambda a: a['date'])
        qty = existing_qty
        for dictionary in intermediate_result:
            if dictionary['move_type'] != 'existing':
                qty += dictionary['qty']
            result += [{
                'proc_id': dictionary['proc_id'],
                'product_id': product_id,
                'location_id': dictionary['location_id'],
                'move_type': dictionary['move_type'],
                'date': dictionary['date'],
                'qty': qty,
                'move_qty': dictionary['qty'],
            }]

        result = sorted(result, key=lambda z: z[parameter_to_sort], reverse=to_reverse)
        result = [x for x in result if x['move_type'] in list_move_types]
        if limit:
            return result[:limit]
        else:
            return result


class StockComputeAll(models.TransientModel):
    _inherit = 'procurement.order.compute.all'

    compute_all = fields.Boolean(string=u"Traiter l'ensemble des produits", default=True)
    product_ids = fields.Many2many('product.product', string=u"Produits à traiter")

    @api.multi
    def procure_calculation(self):
        return super(StockComputeAll, self.with_context(compute_product_ids=self.product_ids.ids,
                                                        compute_all_products=self.compute_all)).procure_calculation()


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
CREATE OR REPLACE VIEW stock_levels_report AS (
    WITH RECURSIVE top_parent(id, top_parent_id) AS (
        SELECT
            sl.id,
            sl.id AS top_parent_id
        FROM
            stock_location sl
            LEFT JOIN stock_location slp ON sl.location_id = slp.id
        WHERE
            sl.usage = 'internal' AND (sl.location_id IS NULL OR slp.usage <> 'internal')
        UNION
        SELECT
            sl.id,
            tp.top_parent_id
        FROM
            stock_location sl, top_parent tp
        WHERE
            sl.usage = 'internal' AND sl.location_id = tp.id
    )
    SELECT
        foo.product_id :: TEXT || '-'
        || foo.location_id :: TEXT || '-'
        || coalesce(foo.move_id :: TEXT, 'existing') AS id,
        foo.product_id,
        pt.categ_id                                  AS product_categ_id,
        foo.location_id                              AS location_id,
        foo.other_location_id,
        foo.move_type,
        sum(foo.qty)
        OVER (PARTITION BY foo.location_id, foo.product_id
            ORDER BY date)                           AS qty,
        foo.date                                     AS date,
        foo.qty                                      AS move_qty
    FROM
        (
            SELECT
                sq.product_id      AS product_id,
                tp.top_parent_id   AS location_id,
                NULL               AS other_location_id,
                'existing' :: TEXT AS move_type,
                max(sq.in_date)    AS date,
                sum(sq.qty)        AS qty,
                NULL               AS move_id
            FROM
                stock_quant sq
                LEFT JOIN stock_location sl ON sq.location_id = sl.id
                LEFT JOIN top_parent tp ON sq.location_id = tp.id
            WHERE
                sl.usage = 'internal' :: TEXT OR sl.usage = 'transit' :: TEXT
            GROUP BY sq.product_id, tp.top_parent_id
            UNION ALL
            SELECT
                sm.product_id    AS product_id,
                tp.top_parent_id AS location_id,
                sm.location_id   AS other_location_id,
                'in' :: TEXT     AS move_type,
                sm.date_expected AS date,
                sm.product_qty   AS qty,
                sm.id            AS move_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                LEFT JOIN top_parent tp ON sm.location_dest_id = tp.id
            WHERE
                (sl.usage = 'internal' :: TEXT OR sl.usage = 'transit' :: TEXT)
                AND sm.state :: TEXT <> 'cancel' :: TEXT
                AND sm.state :: TEXT <> 'done' :: TEXT
                AND sm.state :: TEXT <> 'draft' :: TEXT
            UNION ALL
            SELECT
                sm.product_id       AS product_id,
                tp.top_parent_id    AS location_id,
                sm.location_dest_id AS other_location_id,
                'out' :: TEXT       AS move_type,
                sm.date_expected    AS date,
                -sm.product_qty     AS qty,
                sm.id               AS move_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_id = sl.id
                LEFT JOIN top_parent tp ON sm.location_id = tp.id
            WHERE
                (sl.usage = 'internal' :: TEXT OR sl.usage = 'transit' :: TEXT)
                AND sm.state :: TEXT <> 'cancel' :: TEXT
                AND sm.state :: TEXT <> 'done' :: TEXT
                AND sm.state :: TEXT <> 'draft' :: TEXT
        ) foo
        LEFT JOIN product_product pp ON foo.product_id = pp.id
        LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
)
        """)