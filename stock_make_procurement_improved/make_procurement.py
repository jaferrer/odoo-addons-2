# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import datetime
from odoo import api, fields, models, _


class MakeProcurementLine(models.TransientModel):
    _name = 'make.procurement.line'

    name = fields.Many2one('product.product', u"Variant", required=True, readonly=True)
    make_procurement_id = fields.Many2one(
        'make.procurement', u"Make Procurements", required=True, readonly=True)
    qty = fields.Float(
        u"Quantity", required=True, default=0, readonly=False, store=True)
    date_planned = fields.Date(u"Planned date", required=True)
    uom_id = fields.Many2one('product.uom', u'Unit of Measure', required=True)


class MakeProcurementImproved(models.TransientModel):
    _inherit = 'make.procurement'

    make_procurement_line_ids = fields.One2many(
        'make.procurement.line', 'make_procurement_id', string=u"Make Procurement Line", required=False)
    default_line_date_planned = fields.Date(u"Planned date", required=False)

    @api.onchange('default_line_date_planned')
    def _onchange_default_line_date_planned(self):
        for line in self.make_procurement_line_ids:
            line.date_planned = self.default_line_date_planned

    @api.model
    def create(self, values):
        res = super(MakeProcurementImproved, self).create(values)
        if res.product_tmpl_id:
            if len(res.product_tmpl_id.product_variant_ids) > 1:
                for product in res.product_tmpl_id.product_variant_ids:
                    self.env['make.procurement.line'].create({
                        'name': product.id,
                        'make_procurement_id': res.id,
                        'uom_id': product.uom_id.id,
                        'date_planned': res.date_planned,
                    })
        return res

    @api.multi
    def make_procurement(self):
        if self.product_variant_count <= 1:
            return super(MakeProcurementImproved, self).make_procurement()

        for wizard in self:
            procurements_creates = []
            for line in wizard.make_procurement_line_ids:
                if line.qty > 0:
                    date = fields.Datetime.from_string(line.date_planned)
                    date = date + datetime.timedelta(hours=12)
                    date = fields.Datetime.to_string(date)
                    procurements_creates.append(self.env['procurement.order'].create({
                        'name': 'INT: %s' % (self.env.user.login),
                        'date_planned': date,
                        'product_id': line.name.id,
                        'product_qty': line.qty,
                        'product_uom': line.uom_id.id,
                        'warehouse_id': wizard.warehouse_id.id,
                        'location_id': wizard.warehouse_id.lot_stock_id.id,
                        'company_id': wizard.warehouse_id.company_id.id,
                        'route_ids': [(6, 0, wizard.route_ids.ids)]}).id)
        return {
            'name': _(u"Procurements creates"),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'procurement.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', procurements_creates)]
        }


class ProductTmplImproved(models.Model):
    _inherit = 'product.template'

    @api.multi
    def launch_make_procurement_wizard(self):
        self.ensure_one()
        wizard_id = self.env['make.procurement'].with_context(
            {'active_id': self.id, 'active_model': 'product.template'}).create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _(u"Make Procurements"),
            'res_model': 'make.procurement',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard_id.id,
            'view_id': self.env.ref('stock.view_make_procurment_wizard').id,
            'target': 'new',
        }
