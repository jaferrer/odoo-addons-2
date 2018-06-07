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


class ExpeditionByOrderLineSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    procurements_missing_qty = fields.Float(string=u"Procurement orders missing quantity",
                                            compute='_compute_procurements_missing_qty', store=True)

    @api.depends('product_uom_qty', 'procurement_ids', 'procurement_ids.product_qty', 'procurement_ids.product_uom',
                 'procurement_ids.state')
    def _compute_procurements_missing_qty(self):
        for rec in self:
            procurements_missing_qty = rec.product_uom_qty
            if rec.product_id and rec.product_id.type != 'service':
                procurements_missing_qty -= sum([self.env['product.uom'].
                                                _compute_qty(proc.product_uom.id, proc.product_qty, rec.product_uom.id)
                                                 for proc in rec.procurement_ids if
                                                 proc.state not in ['confirmed', 'cancel']])
            rec.procurements_missing_qty = procurements_missing_qty


class ProcurementSaleLink(models.Model):
    _name = 'procurement.sale.link'
    _order = 'sale_date_planned, proc_date_planned'

    procurement_id = fields.Many2one('procurement.order', string=u"Procurement Order", readonly=True,
                                     domain=[('state', 'not in', ['draft', 'done', 'cancel'])],
                                     context={'display_products_qties_dates': True})
    proc_date_planned = fields.Datetime(string=u"Procurement date", readonly=True,
                                        related='procurement_id.date_planned', store=True)
    partner_id = fields.Many2one('res.partner', string=u"Client", readonly=True)
    product_id = fields.Many2one('product.product', string=u"Product", readonly=True)
    product_qty = fields.Float(string=u"Quantity", readonly=True)
    product_uom = fields.Many2one('product.uom', string=u"Unit", readonly=True)
    origin = fields.Char(string=u"Procurement origin", readonly=True, related='procurement_id.origin', store=True)
    sale_line_id = fields.Many2one('sale.order.line', string=u"Sale order line")
    sale_id = fields.Many2one('sale.order', string=u"Sale order", related='sale_line_id.order_id',
                              store=True, readonly=True)
    sale_date_planned = fields.Datetime(string=u"Sale date", readonly=True, related='sale_line_id.date_planned',
                                        store=True)
    expedition_move_id = fields.Many2one('stock.move', string=u"Expedition move", related='procurement_id.move_dest_id',
                                         store=True, readonly=True)

    @api.model
    def update_table(self):
        self.env.cr.execute("""TRUNCATE TABLE procurement_sale_link RESTART IDENTITY;""")
        query = """INSERT INTO procurement_sale_link
(procurement_id,
 proc_date_planned,
 partner_id,
 product_id,
 product_qty,
 product_uom,
 origin,
 sale_line_id,
 sale_id,
 sale_date_planned,
 expedition_move_id)

  WITH expedition_locations AS (
      SELECT pr.location_src_id AS location_id
      FROM procurement_rule pr
        INNER JOIN stock_location pr_src_loc ON pr_src_loc.id = pr.location_src_id
        INNER JOIN stock_location pr_dest_loc ON pr_dest_loc.id = pr.location_id
      WHERE coalesce(pr.active, FALSE) IS TRUE AND
            pr.action = 'move' AND
            pr_src_loc.usage != 'customer' AND
            pr_dest_loc.usage = 'customer'
  ),

      procurements_no_sol AS (
        SELECT
          po.id                        AS procurement_id,
          po.date_planned :: TIMESTAMP AS proc_date_planned,
          po.partner_dest_id           AS partner_id,
          po.product_id,
          po.product_qty,
          po.product_uom,
          po.origin,
          po.sale_line_id,
          po.sale_id,
          NULL :: TIMESTAMP            AS sale_date_planned,
          po.move_dest_id              AS expedition_move_id
        FROM procurement_order po
          INNER JOIN expedition_locations el ON el.location_id = po.location_id
          LEFT JOIN stock_move sm ON sm.state NOT IN ('draft', 'done', 'cancel') AND sm.id = po.move_dest_id
          LEFT JOIN stock_picking_type spt ON spt.id = sm.picking_type_id
          LEFT JOIN product_product pp ON pp.id = po.product_id
          LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE po.state NOT IN ('draft', 'done', 'cancel') AND
              (po.move_dest_id IS NULL OR spt.code = 'outgoing') AND
              (po.product_id IS NULL OR pt.type = 'product')
        GROUP BY po.id),

      sol_no_procs AS (
        SELECT
          NULL :: INTEGER                           AS procurement_id,
          NULL :: TIMESTAMP                         AS proc_date_planned,
          so.partner_id                             AS partner_id,
          sol.product_id,
          coalesce(sol.procurements_missing_qty, 0) AS product_qty,
          sol.product_uom,
          NULL :: CHARACTER                         AS origin,
          sol.id                                    AS sale_line_id,
          sol.order_id                              AS sale_id,
          sol.date_planned :: TIMESTAMP             AS sale_date_planned,
          NULL :: INTEGER                           AS expedition_move_id
        FROM sale_order_line sol
          LEFT JOIN sale_order so ON so.id = sol.order_id
          LEFT JOIN product_product pp ON pp.id = sol.product_id
          LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE so.state NOT IN ('draft', 'done', 'cancel') AND
              coalesce(sol.procurements_missing_qty, 0) > 0 AND
              (sol.product_id IS NULL OR pt.type = 'product')
    )

  SELECT *
  FROM procurements_no_sol
  UNION
  SELECT *
  FROM sol_no_procs"""
        self.env.cr.execute(query)

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
        if float_compare(procurement_qty_line_uom, sale_line.procurements_missing_qty,
                         precision_rounding=sale_line.product_uom.rounding) > 0:
            raise exceptions. \
                except_orm(_(u"Error!"),
                           _(u"Impossible to rattach more than %s %s to this sale order line") %
                           (sale_line.procurements_missing_qty, sale_line.product_uom.display_name))

    @api.model
    def get_missing_part_for_line(self, sale_line):
        missing_part_for_line = self.search([('sale_line_id', '=', sale_line.id),
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
            qty_comp = float_compare(sale_line.procurements_missing_qty, 0,
                                     precision_rounding=sale_line.product_uom.rounding)
            if qty_comp <= 0:
                missing_part_for_line.unlink()
            else:
                missing_part_for_line.product_qty = sale_line.procurements_missing_qty
        else:
            sale_line.increase_or_create_link()

    @api.multi
    def increase_or_create_link(self, sale_line):
        missing_part_for_line = self.get_missing_part_for_line(sale_line)
        if not missing_part_for_line:
            self.create({
                'partner_id': sale_line.order_id.partner_id.id,
                'product_id': sale_line.product_id.id,
                'product_qty': sale_line.procurements_missing_qty,
                'product_uom': sale_line.product_uom._id,
                'sale_line_id': sale_line.id,
            })
        else:
            missing_part_for_line.product_qty = sale_line.procurements_missing_qty

    @api.multi
    def write(self, vals):
        if 'sale_line_id' in vals:
            sale_line_id = vals.get('sale_line_id')
            if sale_line_id:
                sale_line = self.env['sale.order.line'].search([('id', '=', sale_line_id)])
                self.check_order_state(sale_line)
                for rec in self:
                    procurement_id = vals.get('procurement_id', rec.procurement_id and rec.procurement_id.id or False)
                    if not procurement_id:
                        continue
                    procurement = self.env['procurement.order'].browse(procurement_id)
                    self.check_procurement_state(procurement)
                    self.check_new_link_qty(procurement, sale_line)
                    old_line = procurement.sale_line_id
                    procurement.sale_line_id = sale_line
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
                    sale_line = procurement.sale_line_id
                    if sale_line:
                        self.check_order_state(sale_line)
                        procurement.sale_line_id = False
                        self.increase_or_create_link(sale_line)
        return super(ProcurementSaleLink, self).write(vals)
