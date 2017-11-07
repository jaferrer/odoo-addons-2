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
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.tools import float_compare, float_round, flatten
from openerp.tools.sql import drop_view_if_exists
from openerp import fields, models, api, exceptions, _
import datetime

ORDERPOINT_CHUNK = 1

_logger = logging.getLogger(__name__)


@job(default_channel='root.procurement_just_in_time')
def process_orderpoints(session, model_name, ids, context):
    """Processes the given orderpoints."""
    _logger.info("<<Started chunk of %s orderpoints to process" % ORDERPOINT_CHUNK)
    orderpoints = session.env[model_name].with_context(context).search([('id', 'in', ids)],
                                                                       order='stock_scheduler_sequence desc')
    orderpoints.process()
    job_uuid = session.context.get('job_uuid')
    if job_uuid:
        line = session.env['stock.scheduler.controller'].search([('job_uuid', '=', job_uuid),
                                                                 ('done', '=', False)])
        line.write({'done': True,
                    'date_done': fields.Datetime.now()})


class StockLocation(models.Model):
    _inherit = 'stock.location'

    stock_scheduler_sequence = fields.Integer(string=u"Stock scheduler sequence",
                                              help=u"Same order as the logistic flow")


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    stock_scheduler_sequence = fields.Integer(string=u"Stock scheduler sequence",
                                              help=u"Highest sequences will be processed first")


class StockMove(models.Model):
    _inherit = 'stock.move'

    procurement_id = fields.Many2one('procurement.order', index=True)


class ProcurementOrderQuantity(models.Model):
    _inherit = 'procurement.order'

    move_dest_id = fields.Many2one('stock.move', index=True)
    product_id = fields.Many2one('product.product', index=True)
    state = fields.Selection(index=True)
    qty = fields.Float(string="Quantity", digits_compute=dp.get_precision('Product Unit of Measure'),
                       help='Quantity in the default UoM of the product', compute="_compute_qty", store=True)

    @api.multi
    @api.depends('product_qty', 'product_uom')
    def _compute_qty(self):
        for m in self:
            qty = self.env['product.uom']._compute_qty_obj(m.product_uom, m.product_qty, m.product_id.uom_id)
            m.qty = qty

    @api.multi
    def run_cascade(self, autocommit=False):
        self.run(autocommit=autocommit)
        for rec in self:
            if rec.state == 'running' and rec.rule_id:
                if rec.rule_id.action == 'move':
                    procs = self.search([('move_dest_id.procurement_id', '=', rec.id), ('state', '=', 'confirmed')])
                    procs.run_cascade()
                elif rec.rule_id.action == 'manufacture':
                    mrp = rec.production_id
                    if mrp:
                        procs = self.search([('move_dest_id.raw_material_production_id', '=', mrp.id),
                                             ('state', '=', 'confirmed')])
                        procs.run_cascade()

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        """
        Create procurement based on orderpoint

        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing each procurement.
            This is appropriate for batch jobs only.
        """
        orderpoint_env = self.env['stock.warehouse.orderpoint']
        dom = company_id and [('company_id', '=', company_id)] or []
        if self.env.context.get('compute_product_ids') and not self.env.context.get('compute_all_products'):
            dom += [('product_id', 'in', self.env.context.get('compute_product_ids'))]
        if self.env.context.get('compute_supplier_ids') and not self.env.context.get('compute_all_products'):
            supplierinfo_ids = self.env['product.supplierinfo']. \
                search([('name', 'in', self.env.context['compute_supplier_ids'])])
            read_supplierinfos = supplierinfo_ids.read(['id', 'product_tmpl_id'], load=False)
            dom += [('product_id.product_tmpl_id', 'in', [item['product_tmpl_id'] for item in read_supplierinfos])]
        orderpoints = orderpoint_env.search(dom)

        self.env.cr.execute("""INSERT INTO stock_scheduler_controller
(orderpoint_id,
product_id,
location_id,
stock_scheduler_sequence,
done,
create_date,
write_date,
create_uid,
write_uid)
 
 SELECT
  op.id                                                 AS orderpoint_id,
  op.product_id,
  op.location_id,
  max(COALESCE(sl.stock_scheduler_sequence, 0)) :: CHAR || '-' ||
  max(COALESCE(sl.stock_scheduler_sequence, 0)) :: CHAR AS stock_scheduler_sequence,
  FALSE                                                 AS done,
  CURRENT_TIMESTAMP                                     AS create_date,
  CURRENT_TIMESTAMP                                     AS write_date,
  %s                                                    AS create_uid,
  %s                                                    AS write_uid
FROM stock_warehouse_orderpoint op
  LEFT JOIN stock_location sl ON sl.id = op.location_id
  LEFT JOIN product_product pp ON pp.id = op.product_id
  LEFT JOIN stock_route_product rel ON rel.product_id = pp.product_tmpl_id
  LEFT JOIN stock_location_route slr ON slr.id = rel.route_id
  WHERE op.id IN %s
  GROUP BY op.id""", (self.env.uid, self.env.uid, tuple(orderpoints.ids + [0])))
        return {}

    @api.multi
    def cancel(self):
        result = super(ProcurementOrderQuantity, self).cancel()
        if self.env.context.get('unlink_all_chain'):
            delete_moves_cancelled_by_planned = bool(self.env['ir.config_parameter'].get_param(
                'stock_procurement_just_in_time.delete_moves_cancelled_by_planned', default=False))
            if delete_moves_cancelled_by_planned:
                moves_to_unlink = self.env['stock.move']
                procurements_to_unlink = self.env['procurement.order']
                for rec in self:
                    parent_moves = self.env['stock.move'].search([('procurement_id', '=', rec.id)])
                    for move in parent_moves:
                        if move.state == 'cancel':
                            moves_to_unlink += move
                            if procurements_to_unlink not in procurements_to_unlink and move.procurement_id and \
                                move.procurement_id.state == 'cancel' and \
                                    not any([move.state == 'done' for move in move.procurement_id.move_ids]):
                                procurements_to_unlink += move.procurement_id
                if moves_to_unlink:
                    moves_to_unlink.unlink()
                if procurements_to_unlink:
                    procurements_to_unlink.unlink()
        return result

    @api.model
    def propagate_cancel(self, procurement):
        """
        Improves the original propagate_cancel, in order to cancel it even if one of its moves is done.
        """
        ignore_move_ids = procurement.rule_id.action == 'move' and procurement.move_ids and \
            procurement.move_ids.filtered(lambda move: move.state == 'done').ids or []
        if procurement.rule_id.action == 'move':
            # Keep proc with new qty if some moves are already done
            procurement.remove_done_moves()
        return super(ProcurementOrderQuantity,
                     self.sudo().with_context(ignore_move_ids=ignore_move_ids)).propagate_cancel(procurement)

    @api.model
    def remove_done_moves(self):
        """Splits the given procs creating a copy with the qty of their done moves and set to done.
        """
        for procurement in self:
            if procurement.rule_id.action == 'move':
                qty_done = sum([move.product_qty for move in procurement.move_ids if move.state == 'done'])
                qty_done_proc_uom = self.env['product.uom']. \
                    _compute_qty_obj(procurement.product_id.uom_id, qty_done, procurement.product_uom)
                if procurement.product_uos:
                    qty_done_proc_uos = float_round(
                        self.env['product.uom']._compute_qty_obj(procurement.product_id.uom_id, qty_done,
                                                                 procurement.product_uos),
                        precision_rounding=procurement.product_uos.rounding
                    )
                else:
                    qty_done_proc_uos = float_round(qty_done_proc_uom,
                                                    precision_rounding=procurement.product_uom.rounding)
                if float_compare(qty_done, 0.0, precision_rounding=procurement.product_id.uom_id.rounding) > 0:
                    procurement.write({
                        'product_qty': float_round(qty_done_proc_uom,
                                                   precision_rounding=procurement.product_uom.rounding),
                        'product_uos_qty': qty_done_proc_uos,
                    })


class StockMoveJustInTime(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_cancel(self):
        domain = [('id', 'in', self.ids),
                  ('id', 'not in', (self.env.context.get('ignore_move_ids') or []))]
        if self.env.context.get('do_not_try_to_cancel_done_moves'):
            domain += [('state', '!=', 'done')]
        moves_to_cancel = self.search(domain)
        return super(StockMoveJustInTime, moves_to_cancel).action_cancel()


class StockWarehouseOrderPointJit(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    stock_scheduler_sequence = fields.Integer(string=u"Stock scheduler sequence", default=1000,
                                              related='location_id.stock_scheduler_sequence', store=True, readonly=True)

    @api.multi
    def get_list_events(self):
        """Returns a dict of stock level requirements where the stock level is below minimum qty for the product and
        the location of the orderpoint."""
        self.ensure_one()
        events = self.compute_stock_levels_requirements(product_id=self.product_id.id, location=self.location_id,
                                                        list_move_types=('in', 'planned', 'out', 'existing'),
                                                        limit=False, parameter_to_sort='date', to_reverse=False)
        return sorted(events, key=lambda event: event['date'])

    @api.multi
    def create_from_need(self, need, stock_after_event):
        """Creates a procurement to fulfill the given need with the data calculated from the given order point.
        Will set the date of the procurement at the date of the need.

        :param need: the 'stock levels requirements' dictionary to fulfill
        """
        proc = self.env['procurement.order']
        self.ensure_one()
        product_max_qty = self.get_max_qty(fields.Datetime.from_string(need['date']))
        if self.fill_strategy == 'duration':
            consider_end_contract_effect = bool(self.env['ir.config_parameter'].get_param(
                'stock_procurement_just_in_time.consider_end_contract_effect', default=False))
            if not consider_end_contract_effect:
                product_max_qty += self.product_min_qty
        qty = max(max(self.product_min_qty, product_max_qty) - stock_after_event, 0)
        reste = self.qty_multiple > 0 and qty % self.qty_multiple or 0.0
        if float_compare(reste, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            qty += self.qty_multiple - reste
        qty = float_round(qty, precision_rounding=self.product_uom.rounding)

        if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            proc_vals = proc._prepare_orderpoint_procurement(self, qty)
            if need['date']:
                proc_vals.update({'date_planned': need['date']})
            proc = proc.create(proc_vals)
            if not self.env.context.get('procurement_no_run'):
                proc.run_cascade()
            _logger.debug("Created proc: %s, (%s, %s). Product: %s, Location: %s" %
                          (proc, proc.date_planned, proc.product_qty, self.product_id, self.location_id))
        else:
            _logger.debug("Requested qty is null, no procurement created")
        return proc

    @api.multi
    def get_last_scheduled_date(self):
        """Returns the last scheduled date for this order point."""
        self.ensure_one()
        last_schedule = self.env['stock.warehouse.orderpoint'].compute_stock_levels_requirements(
            product_id=self.product_id.id,
            location=self.location_id,
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
        for rec in self:
            # We get all running procurements placed after timestamp.
            procs = self.env['procurement.order'].search([('product_id', '=', rec.product_id.id),
                                                          ('location_id', '=', rec.location_id.id),
                                                          ('state', 'not in', ['done', 'cancel']),
                                                          ('date_planned', '>', fields.Datetime.to_string(timestamp))])
            if procs:
                _logger.debug("Removing not needed procurements: %s", procs.ids)
                procs.with_context(unlink_all_chain=True, cancel_procurement=True).cancel()
                procs.unlink()

    @api.multi
    def get_max_allowed_qty(self, need):
        self.ensure_one()
        product_max_qty = self.get_max_qty(fields.Datetime.from_string(need['date']))
        if self.fill_strategy == 'duration':
            consider_end_contract_effect = bool(self.env['ir.config_parameter'].get_param(
                'stock_procurement_just_in_time.consider_end_contract_effect', default=False))
            if not consider_end_contract_effect:
                product_max_qty += self.product_min_qty
        if self.qty_multiple and product_max_qty % self.qty_multiple != 0:
            product_max_qty = (product_max_qty // self.qty_multiple + 1) * self.qty_multiple
        relative_stock_delta = float(self.env['ir.config_parameter'].get_param(
            'stock_procurement_just_in_time.relative_stock_delta', default=0))
        absolute_stock_delta = float(self.env['ir.config_parameter'].get_param(
            'stock_procurement_just_in_time.absolute_stock_delta', default=0))
        return max((1 * float(relative_stock_delta) / 100) * product_max_qty, product_max_qty + absolute_stock_delta)

    @api.multi
    def is_over_stock_max(self, need, stock_after_event):
        self.ensure_one()
        max_qty = self.get_max_allowed_qty(need)
        if float_compare(stock_after_event, max_qty, precision_rounding=self.product_id.uom_id.rounding) > 0:
            return True
        return False

    @api.multi
    def is_under_stock_min(self, stock_after_event):
        self.ensure_one()
        min_qty = self.product_min_qty
        if float_compare(stock_after_event, min_qty, precision_rounding=self.product_id.uom_id.rounding) < 0:
            return True
        return False

    @api.multi
    def process(self):
        """Process this orderpoint."""
        for op in self:
            _logger.debug("Computing orderpoint %s (%s, %s, %s)" % (op.id, op.name, op.product_id.display_name,
                                                                    op.location_id.display_name))
            events = op.get_list_events()
            done_dates = []
            events_at_date = []
            stock_after_event = 0
            for event in events:
                if event['date'] not in done_dates:
                    events_at_date = [item for item in events if item['date'] == event['date']]
                    stock_after_event += sum(item['move_qty'] for item in events_at_date)
                    done_dates += [event['date']]
                if op.is_over_stock_max(event, stock_after_event) and event['move_type'] in ['in', 'planned']:
                    proc_oversupply = self.env['procurement.order'].search([('id', '=', event['proc_id']),
                                                                            ('state', '!=', 'done')])
                    qty_same_proc = sum(item['move_qty'] for item in events if item['proc_id'] == event['proc_id'])
                    if proc_oversupply:
                        stock_after_event -= qty_same_proc
                        _logger.debug("Oversupply detected: deleting procurement %s " % proc_oversupply.id)
                    proc_oversupply.with_context(unlink_all_chain=True, cancel_procurement=True).cancel()
                    proc_oversupply.unlink()
                    if op.is_under_stock_min(stock_after_event) and \
                            any([item['move_type'] == 'out' for item in events_at_date]):
                        new_proc = op.create_from_need(event, stock_after_event)
                        stock_after_event += new_proc and new_proc.product_qty or 0
                elif op.is_under_stock_min(stock_after_event):
                    new_proc = op.create_from_need(event, stock_after_event)
                    stock_after_event += new_proc and new_proc.product_qty or 0
            # Now we want to make sure that at the end of the scheduled outgoing moves, the stock level is
            # the minimum quantity of the orderpoint.
            last_scheduled_date = op.get_last_scheduled_date()
            if last_scheduled_date:
                date_end = last_scheduled_date + relativedelta(minutes=+1)
                op.remove_unecessary_procurements(date_end)

    @api.model
    def compute_stock_levels_requirements(self, product_id, location, list_move_types, limit=1,
                                          parameter_to_sort='date', to_reverse=False, max_date=None):
        """
        Computes stock level report
        :param product_id: int
        :param location: recordset
        :param list_move_types: tuple or list of strings (move types)
        :param limit: maximum number of lines in the result
        :param parameter_to_sort: str
        :param to_reverse: bool
        :return: list of need dictionaries
        """
        procurement_date_clause = max_date and " AND po.date_planned <= %s " or ""
        move_out_date_clause = max_date and " AND sm.date <= %s " or ""
        move_in_date_clause = max_date and " AND COALESCE(po.date_planned, sm.date) <= %s " or ""
        # Workaround for tests
        if not location.parent_left or not location.parent_right:
            self.env['stock.location']._parent_store_compute()
        params = (product_id, location.parent_left, location.parent_right)
        if max_date:
            params += (max_date,)

        # Computing the top parent location
        first_date = False
        result = []
        intermediate_result = []
        query_moves_in = """
            SELECT
                sm.id,
                sm.product_qty,
                min(COALESCE(po.date_planned, sm.date)) AS date,
                po.id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                LEFT JOIN procurement_order po ON sm.procurement_id = po.id
            WHERE
                sm.product_id = %s
                AND sm.state NOT IN ('cancel', 'done', 'draft')
                AND sl.parent_left >= %s
                AND sl.parent_left < %s""" + \
                         move_in_date_clause + \
                         """GROUP BY sm.id, po.id, sm.product_qty
                         ORDER BY DATE"""
        self.env.cr.execute(query_moves_in, params)
        moves_in_tuples = self.env.cr.fetchall()

        query_moves_out = """
            SELECT
                sm.id,
                sm.product_qty,
                min(sm.date) AS date
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_id = sl.id
            WHERE
                sm.product_id = %s
                AND sm.state NOT IN ('cancel', 'done', 'draft')
                AND sl.parent_left >= %s
                AND sl.parent_left < %s""" + \
                          move_out_date_clause + \
                          """
                          GROUP BY sm.id, sm.product_qty
                          ORDER BY date
                      """
        self.env.cr.execute(query_moves_out, params)
        moves_out_tuples = self.env.cr.fetchall()

        stock_quant_restricted = self.env['stock.quant'].search([('product_id', '=', product_id),
                                                                 ('location_id', 'child_of', location.id)])
        query_procs = """
            SELECT
                po.id,
                min(po.date_planned),
                min(po.qty)
            FROM
                procurement_order po
                LEFT JOIN stock_location sl ON po.location_id = sl.id
                LEFT JOIN stock_move sm ON po.id = sm.procurement_id
            WHERE
                po.product_id = %s
                AND sl.parent_left >= %s
                AND sl.parent_left < %s
                AND po.state NOT IN ('done', 'cancel')
                AND (sm.state = 'draft' OR sm.id IS NULL)""" + \
                      procurement_date_clause + \
                      """
                      GROUP BY po.id
                      ORDER BY po.date_planned
                  """
        self.env.cr.execute(query_procs, params)
        procurement_tuples = self.env.cr.fetchall()
        dates = []
        if moves_in_tuples:
            dates += [moves_in_tuples[0][2]]
        if moves_out_tuples:
            dates += [moves_out_tuples[0][2]]
        if procurement_tuples:
            dates += [procurement_tuples[0][1]]
        if dates:
            first_date = min(dates)

        # existing items
        existing_qty = sum([x.qty for x in stock_quant_restricted])
        intermediate_result += [{
            'proc_id': False,
            'location_id': location.id,
            'move_type': 'existing',
            'date': first_date,
            'move_qty': existing_qty,
            'move_id': False,
        }]
        # incoming items
        for sm in moves_in_tuples:
            intermediate_result += [{
                'proc_id': sm[3],
                'location_id': location.id,
                'move_type': 'in',
                'date': sm[2],
                'move_qty': sm[1],
                'move_id': sm[0],
            }]

        # outgoing items
        for sm in moves_out_tuples:
            intermediate_result += [{
                'proc_id': False,
                'location_id': location.id,
                'move_type': 'out',
                'date': sm[2],
                'move_qty': - sm[1],
                'move_id': sm[0],
            }]

        # planned items
        for po in procurement_tuples:
            intermediate_result += [{
                'proc_id': po[0],
                'location_id': location.id,
                'move_type': 'planned',
                'date': po[1],
                'move_qty': po[2],
                'move_id': False,
            }]

        intermediate_result = sorted(intermediate_result, key=lambda a: a['date'])
        qty = 0
        while intermediate_result:
            stock_levels = [item for item in intermediate_result if item['date'] == intermediate_result[0]['date']]
            total_qty = sum([item['move_qty'] for item in stock_levels])
            qty += total_qty
            for dictionary in stock_levels[:]:
                intermediate_result.remove(dictionary)
                if dictionary['move_type'] not in list_move_types:
                    continue
                level_qty = dictionary['move_qty']
                if dictionary['move_type'] != 'existing':
                    level_qty = qty
                result += [{
                    'proc_id': dictionary['proc_id'],
                    'product_id': product_id,
                    'location_id': dictionary['location_id'],
                    'move_type': dictionary['move_type'],
                    'date': dictionary['date'],
                    'qty': level_qty,
                    'move_qty': dictionary['move_qty'],
                }]
        result = sorted(result, key=lambda z: z[parameter_to_sort], reverse=to_reverse)
        if limit:
            return result[:limit]
        else:
            return result


class StockLevelsReport(models.Model):
    _name = "stock.levels.report"
    _description = "Stock Levels Report"
    _order = "date"
    _auto = False

    id = fields.Integer("ID", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", index=True)
    product_categ_id = fields.Many2one("product.category", string="Product Category")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", index=True)
    other_warehouse_id = fields.Many2one("stock.warehouse", string="Origin/Destination")
    move_type = fields.Selection([('existing', 'Existing'), ('in', 'Incoming'), ('out', 'Outcoming')],
                                 string="Move Type", index=True)
    date = fields.Datetime("Date", index=True)
    qty = fields.Float("Stock Quantity", group_operator="last")
    move_qty = fields.Float("Moved Quantity")

    def init(self, cr):
        drop_view_if_exists(cr, "stock_levels_report")
        cr.execute("""CREATE OR REPLACE VIEW stock_levels_report AS (
    WITH
            link_location_warehouse AS (
                SELECT
                    sl.id AS location_id,
                    sw.id AS warehouse_id
                FROM stock_warehouse sw
                    LEFT JOIN stock_location sl_view ON sl_view.id = sw.view_location_id
                    LEFT JOIN stock_location sl ON sl.parent_left >= sl_view.parent_left AND
                                                   sl.parent_left <= sl_view.parent_right
        ),
            min_product AS (
                SELECT
                    min(sm.date_expected) - INTERVAL '1 second' AS min_date,
                    sm.product_id                               AS product_id
                FROM
                    stock_move sm
                    LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                    LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                    LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
                WHERE ((link_dest.warehouse_id IS NOT NULL
                        AND (link.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id))
                       OR (link.warehouse_id IS NOT NULL
                           AND (link_dest.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)))
                      AND sm.state :: TEXT <> 'cancel' :: TEXT
                      AND sm.state :: TEXT <> 'done' :: TEXT
                      AND sm.state :: TEXT <> 'draft' :: TEXT
                GROUP BY sm.product_id
        )

    SELECT
        foo.product_id :: TEXT || '-'
        || foo.warehouse_id :: TEXT || '-'
        || coalesce(foo.move_id :: TEXT, 'existing') AS id,
        foo.product_id,
        pt.categ_id                                  AS product_categ_id,
        foo.move_type,
        sum(foo.qty)
        OVER (PARTITION BY foo.warehouse_id, foo.product_id
            ORDER BY date)                           AS qty,
        foo.date                                     AS date,
        foo.qty                                      AS move_qty,
        foo.warehouse_id,
        foo.other_warehouse_id
    FROM
        (
            SELECT
                sq.product_id                               AS product_id,
                'existing' :: TEXT                          AS move_type,
                coalesce(min(mp.min_date), max(sq.in_date)) AS date,
                sum(sq.qty)                                 AS qty,
                NULL                                        AS move_id,
                link.warehouse_id,
                NULL                                        AS other_warehouse_id
            FROM
                stock_quant sq
                LEFT JOIN stock_location sl ON sq.location_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sl.location_id
                LEFT JOIN min_product mp ON mp.product_id = sq.product_id
            WHERE link.warehouse_id IS NOT NULL
            GROUP BY sq.product_id, link.warehouse_id

            UNION ALL

            SELECT
                sm.product_id     AS product_id,
                'in' :: TEXT      AS move_type,
                sm.date_expected  AS date,
                sm.product_qty    AS qty,
                sm.id             AS move_id,
                link_dest.warehouse_id,
                link.warehouse_id AS other_warehouse_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_dest_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
            WHERE link_dest.warehouse_id IS NOT NULL
                  AND (link.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)
                  AND sm.state :: TEXT <> 'cancel' :: TEXT
                  AND sm.state :: TEXT <> 'done' :: TEXT
                  AND sm.state :: TEXT <> 'draft' :: TEXT

            UNION ALL

            SELECT
                sm.product_id          AS product_id,
                'out' :: TEXT          AS move_type,
                sm.date_expected       AS date,
                -sm.product_qty        AS qty,
                sm.id                  AS move_id,
                link.warehouse_id,
                link_dest.warehouse_id AS other_warehouse_id
            FROM
                stock_move sm
                LEFT JOIN stock_location sl ON sm.location_id = sl.id
                LEFT JOIN link_location_warehouse link ON link.location_id = sm.location_id
                LEFT JOIN link_location_warehouse link_dest ON link_dest.location_id = sm.location_dest_id
            WHERE link.warehouse_id IS NOT NULL
                  AND (link_dest.warehouse_id IS NULL OR link.warehouse_id != link_dest.warehouse_id)
                  AND sm.state :: TEXT <> 'cancel' :: TEXT
                  AND sm.state :: TEXT <> 'done' :: TEXT
                  AND sm.state :: TEXT <> 'draft' :: TEXT
        ) foo
        LEFT JOIN product_product pp ON foo.product_id = pp.id
        LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
)
        """)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_warehouse_for_stock_report(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)

    @api.multi
    def action_show_evolution(self):
        self.ensure_one()
        warehouse = self.get_warehouse_for_stock_report()
        if warehouse:
            ctx = dict(self.env.context)
            ctx.update({
                'search_default_warehouse_id': warehouse.id,
                'search_default_product_id': self.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Evolution"),
                'res_model': 'stock.levels.report',
                'view_type': 'form',
                'view_mode': 'graph,tree',
                'context': ctx,
            }
        else:
            raise exceptions.except_orm(_("Error"), _("Your company does not have a warehouse"))


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(track_visibility=False)

    @api.model
    def create(self, vals):
        # The creation messages are useless
        return super(StockPicking, self.with_context(mail_notrack=True, mail_create_nolog=True)).create(vals)


class StockSchedulerController(models.Model):
    _name = 'stock.scheduler.controller'
    _order = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string=u"Orderpoint")
    product_id = fields.Many2one('product.product', string=u"Product", readonly=True, required=True)
    location_id = fields.Many2one('stock.location', string=u"Location", readonly=True, required=True)
    stock_scheduler_sequence = fields.Char(string=u"Stock scheduler sequence", readonly=True, group_operator='max')
    job_creation_date = fields.Datetime(string=u"Job Creation Date", readonly=True)
    job_uuid = fields.Char(string=u"Job UUID", readonly=True)
    date_done = fields.Datetime(string=u"Date done")
    done = fields.Boolean(string=u"Done")

    @api.model
    def update_scheduler_controller(self, jobify=True):
        max_running_sequence = self.read_group([('done', '=', False)], ['stock_scheduler_sequence'],
                                               ['stock_scheduler_sequence'], orderby='stock_scheduler_sequence desc',
                                               limit=1)
        if max_running_sequence:
            max_running_sequence = max_running_sequence[0]['stock_scheduler_sequence']
            controller_lines = self.search([('done', '=', False),
                                            ('job_uuid', '=', False),
                                            ('stock_scheduler_sequence', '=', max_running_sequence)])
            for line in controller_lines:
                if jobify:
                    job_uuid = process_orderpoints. \
                        delay(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                              line.orderpoint_id.ids, dict(self.env.context),
                              description="Computing orderpoints for product %s and location %s" %
                                          (line.product_id.name, line.location_id.display_name))
                    line.job_uuid = job_uuid
                    line.write({'job_uuid': job_uuid,
                                'job_creation_date': fields.Datetime.now()})
                else:
                    line.job_uuid = str(line.orderpoint_id.id)
                    self.env.context = dict(self.env.context, job_uuid=line.job_uuid)
                    process_orderpoints(ConnectorSession.from_env(self.env), 'stock.warehouse.orderpoint',
                                        line.orderpoint_id.ids, dict(self.env.context))
