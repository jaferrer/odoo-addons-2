# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, exceptions, _
from openerp.tools import float_compare
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
import openerp.addons.decimal_precision as dp


@job
def job_update_sale_procurement_links(session, model_name, context):
    model = session.env[model_name].with_context(context)
    model.update_table_model()
    return "Procurements/Sale links updated."


class ExpeditionByOrderLineProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    scheduled_for_sale_line_id = fields.Many2one('sale.order.line', string=u"Scheduled for sale order line", index=True)


class ExpeditionByOrderLineSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    procurements_not_scheduled_qty = fields.Float(string=u"Procurement orders missing quantity",
                                                  compute='_compute_procurements_not_scheduled_qty', store=True,
                                                  digits_compute=dp.get_precision('Product UoS'))
    scheduled_procurement_ids = fields.One2many('procurement.order', 'scheduled_for_sale_line_id',
                                                string=u"Procurement orders scheduled for this line")
    manual_consideration = fields.Boolean(string=u"Manual consideration", default=False)

    @api.depends('product_uom_qty', 'scheduled_procurement_ids', 'scheduled_procurement_ids.product_qty',
                 'scheduled_procurement_ids.product_uom', 'scheduled_procurement_ids.state')
    def _compute_procurements_not_scheduled_qty(self):
        for rec in self:
            procurements_not_scheduled_qty = rec.product_uom_qty
            if rec.product_id and rec.product_id.type != 'service':
                procurements_not_scheduled_qty -= sum([self.env['product.uom'].
                                                      _compute_qty(proc.product_uom.id, proc.product_qty,
                                                                   rec.product_uom.id)
                                                       for proc in rec.scheduled_procurement_ids if
                                                       proc.state not in ['confirmed', 'cancel']])
            rec.procurements_not_scheduled_qty = procurements_not_scheduled_qty


class ProcurementSaleLink(models.Model):
    _name = 'procurement.sale.link'
    _order = 'sale_date_planned, proc_date_planned'

    procurement_id = fields.Many2one('procurement.order', string=u"Procurement Order", readonly=True,
                                     domain=[('state', 'not in', ['draft', 'done', 'cancel'])],
                                     context={'display_products_qties_dates': True}, index=True)
    proc_location_id = fields.Many2one('stock.location', string=u"Procurement location", readonly=True,
                                       related='procurement_id.location_id', store=True)
    proc_date_planned = fields.Datetime(string=u"Procurement date", readonly=True,
                                        related='procurement_id.date_planned', store=True)
    partner_id = fields.Many2one('res.partner', string=u"Client", readonly=True)
    product_id = fields.Many2one('product.product', string=u"Product", readonly=True)
    product_qty = fields.Float(string=u"Quantity", readonly=True)
    product_uom = fields.Many2one('product.uom', string=u"Unit", readonly=True)
    origin = fields.Char(string=u"Procurement origin", readonly=True, related='procurement_id.origin', store=True)
    scheduled_for_sale_line_id = fields.Many2one('sale.order.line', string=u"Scheduled for sale order line")
    sale_id = fields.Many2one('sale.order', string=u"Sale order", related='scheduled_for_sale_line_id.order_id',
                              store=True, readonly=True)
    sale_date_planned = fields.Datetime(string=u"Sale date", readonly=True,
                                        related='scheduled_for_sale_line_id.date_planned', store=True)
    sol_manual_consideration = fields.Boolean(
        string=u"Manual consideration", related='scheduled_for_sale_line_id.manual_consideration', store=True)
    sale_warehouse_id = fields.Many2one(string=u"Warehouse", related='sale_id.warehouse_id', store=True)

    lettrable = fields.Boolean(compute=lambda x: None, search='_search_is_lettrable')

    @api.model
    def _search_is_lettrable(self, operator, value):

        product_ids = self.env['sale.order.line'].search([('order_id.state', 'not in', ['draft', 'done', 'cancel']),
                                                          ('remaining_qty', '>', 0.0001)]).mapped('product_id.id')

        psl_ids = self.env['procurement.sale.link'].search(
            [('procurement_id', '!=', False), ('scheduled_for_sale_line_id', '=', False),
             ('product_id', 'in', product_ids)]).ids

        return [('id', 'in', psl_ids)]

    @api.model
    def update_table(self):
        context = dict(self.env.context)
        job_update_sale_procurement_links.delay(ConnectorSession.from_env(self.env), 'procurement.sale.link', context)

    @api.model
    def update_table_model(self):
        self.search([]).sudo().unlink()
        query = """WITH procurements_no_sol AS (
      SELECT
        po.id                        AS procurement_id,
        po.partner_dest_id           AS partner_id,
        po.product_id,
        po.product_qty,
        po.product_uom,
        po.scheduled_for_sale_line_id
      FROM procurement_order po
        LEFT JOIN stock_move sm ON sm.state NOT IN ('draft', 'done', 'cancel') AND sm.id = po.move_dest_id
        LEFT JOIN stock_picking_type spt ON spt.id = sm.picking_type_id
        LEFT JOIN product_product pp ON pp.id = po.product_id
        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
      WHERE po.state NOT IN ('draft', 'done', 'cancel') AND
            po.sale_line_id IS NULL AND
            (po.move_dest_id IS NULL OR spt.code = 'outgoing') AND
            (po.product_id IS NULL OR pt.type = 'product') AND
            po.service_for_production_id IS NULL AND
            po.create_uid != %s
      GROUP BY po.id),

      sol_no_procs AS (
        SELECT
          NULL :: INTEGER                    AS procurement_id,
          so.partner_id                      AS partner_id,
          sol.product_id,
          COALESCE(sol.procurements_not_scheduled_qty, 0) AS product_qty,
          sol.product_uom,
          sol.id                             AS scheduled_for_sale_line_id
        FROM sale_order_line sol
          LEFT JOIN sale_order so ON so.id = sol.order_id
          LEFT JOIN product_product pp ON pp.id = sol.product_id
          LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE so.state NOT IN ('draft', 'done', 'cancel') AND
              COALESCE(sol.procurements_not_scheduled_qty, 0) > 0 AND
              (sol.product_id IS NULL OR pt.type = 'product'))

  SELECT *
  FROM procurements_no_sol
  UNION
  SELECT *
  FROM sol_no_procs"""
        self.env.cr.execute(query, (self.env.ref('base.user_root').id,))
        for item in self.env.cr.dictfetchall():
            self.sudo().create({
                'procurement_id': item['procurement_id'] or False,
                'partner_id': item['partner_id'] or False,
                'product_id': item['product_id'] or False,
                'product_qty': item['product_qty'] or 0,
                'product_uom': item['product_uom'] or False,
                'scheduled_for_sale_line_id': item['scheduled_for_sale_line_id'] or False,
            })

    @api.model
    def check_procurement_state(self, procurement):
        if procurement.state in ['draft', 'done', 'cancel']:
            raise exceptions.except_orm(_(u"Error!"), _(u"Impossible to rattach a procurement in this state."))

    @api.model
    def check_order_state(self, sale_line):
        if sale_line.order_id.state in ['draft', 'done', 'cancel']:
            raise exceptions.except_orm(_(u"Error!"),
                                        _(u"Impossible to rattach a procurement to an order in this state."))

    @api.model
    def check_new_link_qty(self, procurement, sale_line):
        procurement_qty_line_uom = self.env['product.uom']._compute_qty(procurement.product_uom.id,
                                                                        procurement.product_qty,
                                                                        sale_line.product_uom.id)
        if float_compare(procurement_qty_line_uom, sale_line.procurements_not_scheduled_qty,
                         precision_rounding=sale_line.product_uom.rounding) > 0:
            raise exceptions. \
                except_orm(_(u"Error!"),
                           _(u"Impossible to rattach more than %s %s to this sale order line") %
                           (sale_line.procurements_not_scheduled_qty, sale_line.product_uom.display_name))

    @api.model
    def get_missing_part_for_line(self, sale_line):
        missing_part_for_line = self.search([('scheduled_for_sale_line_id', '=', sale_line.id),
                                             ('procurement_id', '=', False)])
        if not missing_part_for_line:
            return
        if len(missing_part_for_line) > 1:
            to_unlink = missing_part_for_line[1:]
            missing_part_for_line = missing_part_for_line[0]
            to_unlink.unlink()
        return missing_part_for_line

    @api.model
    def clean_outdated_links(self, sale_line):
        missing_part_for_line = self.get_missing_part_for_line(sale_line)
        if missing_part_for_line:
            qty_comp = float_compare(sale_line.procurements_not_scheduled_qty, 0,
                                     precision_rounding=sale_line.product_uom.rounding)
            if qty_comp <= 0:
                missing_part_for_line.unlink()
            else:
                missing_part_for_line.product_qty = sale_line.procurements_not_scheduled_qty
        else:
            sale_line.increase_or_create_link()

    @api.multi
    def increase_or_create_link(self, sale_line):
        missing_part_for_line = self.get_missing_part_for_line(sale_line)
        if not missing_part_for_line:
            self.create({
                'partner_id': sale_line.order_id.partner_id.id,
                'product_id': sale_line.product_id.id,
                'product_qty': sale_line.procurements_not_scheduled_qty,
                'product_uom': sale_line.product_uom._id,
                'scheduled_for_sale_line_id': sale_line.id,
            })
        else:
            missing_part_for_line.product_qty = sale_line.procurements_not_scheduled_qty

    @api.multi
    def generate_procurements(self):
        for rec in self:
            if not rec.scheduled_for_sale_line_id:
                raise exceptions. \
                    except_orm(_(u"Error!"),
                               _(u"Impossible to generate a procurement on a line which has no sale order line."))
            if rec.procurement_id:
                continue
            first_move = self.env['stock.move'].search([('sale_line_id', '=', rec.scheduled_for_sale_line_id.id),
                                                        ('state', 'not in', ['draft', 'cancel'])], limit=1)
            if not first_move:
                raise exceptions. \
                    except_orm(_(u"Error!"), _(u"Sale order %s: impossible to determine source location for delivery "
                                               u"slip. Please generate it first.") % rec.sale_id.display_name)
            rec.finalize_procurement_creation(first_move)

    @api.multi
    def manual_consideration(self):
        for rec in self:
            rec.scheduled_for_sale_line_id.manual_consideration = True

    @api.multi
    def finalize_procurement_creation(self, delivery_move):
        self.ensure_one()
        delivery_move.ensure_one()
        self.env['procurement.order'].create({
            'name': self.scheduled_for_sale_line_id.name,
            'origin': self.order_id.name,
            'date_planned': delivery_move.date,
            'product_id': self.scheduled_for_sale_line_id.product_id.id,
            'product_qty': self.scheduled_for_sale_line_id.procurements_not_scheduled_qty,
            'product_uom': self.scheduled_for_sale_line_id.product_uom.id,
            'product_uos_qty': (self.scheduled_for_sale_line_id.product_uos and
                                self.scheduled_for_sale_line_id.product_uos_qty) or
                               self.scheduled_for_sale_line_id.product_uom_qty,
            'product_uos': (self.scheduled_for_sale_line_id.product_uos and
                            self.scheduled_for_sale_line_id.product_uos.id) or
                           self.scheduled_for_sale_line_id.product_uom.id,
            'company_id': self.order_id.company_id.id,
            'group_id': self.order_id.procurement_group_id.id,
            'invoice_state': 'none',
            'sale_line_id': False,
            'scheduled_for_sale_line_id': self.scheduled_for_sale_line_id.id,
        })

    @api.multi
    def write(self, vals):
        if 'scheduled_for_sale_line_id' in vals:
            scheduled_for_sale_line_id = vals.get('scheduled_for_sale_line_id')
            if scheduled_for_sale_line_id:
                sale_line = self.env['sale.order.line'].search([('id', '=', scheduled_for_sale_line_id)])
                self.check_order_state(sale_line)
                for rec in self:
                    procurement_id = vals.get('procurement_id', rec.procurement_id and rec.procurement_id.id or False)
                    if not procurement_id:
                        continue
                    procurement = self.env['procurement.order'].browse(procurement_id)
                    self.check_procurement_state(procurement)
                    self.check_new_link_qty(procurement, sale_line)
                    old_line = procurement.scheduled_for_sale_line_id
                    procurement.scheduled_for_sale_line_id = sale_line
                    self.clean_outdated_links(sale_line)
                    if old_line:
                        self.increase_or_create_link(old_line)
            else:
                for rec in self:
                    procurement_id = vals.get('procurement_id', rec.procurement_id and rec.procurement_id.id or False)
                    if not procurement_id:
                        continue
                    procurement = self.env['procurement.order'].browse(procurement_id)
                    self.check_procurement_state(procurement)
                    sale_line = procurement.scheduled_for_sale_line_id
                    if sale_line:
                        self.check_order_state(sale_line)
                        procurement.scheduled_for_sale_line_id = False
                        self.increase_or_create_link(sale_line)
        return super(ProcurementSaleLink, self).write(vals)
