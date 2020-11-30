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
from odoo import api, fields, models, exceptions, _


class AccountInvoiceToInvoice(models.Model):
    _inherit = 'account.invoice'

    mrp_production_ids = fields.One2many('mrp.production', 'account_invoice_id', string=u"Manufacturing orders")


class ResPartnerToInvoice(models.Model):
    _inherit = 'res.partner'

    is_manufacturer = fields.Boolean(compute=lambda x: None, search='_search_is_manufacturer')

    @api.model
    def _search_is_manufacturer(self, oper, value):
        manufacturers = self.env['stock.picking.type'].search(
            [('code', '=', 'mrp_operation')]).mapped('default_location_dest_id.partner_id')
        if value:
            operande = 'in'
        else:
            operande = 'not in'
        return [('id', operande, manufacturers.ids)]


class MrpProductionToInvoice(models.Model):
    _inherit = 'mrp.production'

    manufacturer_id = fields.Many2one('res.partner', u"Manufacturer", required=False,
                                      domain=[('is_manufacturer', '=', True)])
    account_invoice_id = fields.Many2one('account.invoice', u"Account invoice", required=False)

    @api.multi
    @api.onchange('location_dest_id')
    def _onchange_location_dest_id(self):
        for rec in self:
            rec.manufacturer_id = rec.location_dest_id.partner_id

    @api.multi
    @api.onchange('manufacturer_id')
    def _onchange_manufacturer_id(self):
        for rec in self:
            rec.stock_picking_type = False
            spt = self.env['stock.picking.type'].search(
                [('default_location_dest_id.partner_id', '=', rec.manufacturer_id.id), ('code', '=', 'mrp_operation')])
            if len(spt) == 1:
                rec.picking_type_id = spt

    @api.multi
    def create_ai_from_of(self):
        if [mo for mo in self if not mo.manufacturer_id]:
            raise exceptions.ValidationError(_(u"At least one manufacturing order has not manufacturer!"))

        if len(self.mapped('manufacturer_id')) != 1:
            raise exceptions.ValidationError(
                _(u"It's not possible to generate an invoice from manufacturing orders with different manufacturer!"))
        manufacturer = self.mapped('manufacturer_id')[0]

        if any([mo.account_invoice_id and mo.account_invoice_id.state != 'cancel' for mo in self]):
            raise exceptions.ValidationError(_(u"An invoice already exist for this manufacturing order!"))

        all_services_to_invoice = []
        for rec in self:
            sti = rec.product_id
            seller = sti._select_seller(
                partner_id=manufacturer,
                quantity=rec.product_qty,
                date=rec.date_planned_start[:10],
                uom_id=rec.product_uom_id)
            all_services_to_invoice.append((0, 0, {
                'name': seller.product_name,
                'product_id': sti.id,
                'quantity': rec.product_qty,
                'uom_id': sti.uom_po_id.id,
                'price_unit': seller.price or sti.list_price,
                'account_id': self.env['account.invoice.line'].get_invoice_line_account(
                    'in_invoice', sti, manufacturer.property_account_position_id, self.env.user.company_id).id,
            }))

        ctx = self.env.context.copy()
        ctx.update({
            'default_partner_id': manufacturer.id,
            'default_date_invoice': fields.Datetime.now(),
            'default_invoice_line_ids': all_services_to_invoice,
            'default_state': 'draft',
            'default_type': 'in_invoice',
            'default_journal_type': 'purchase',
            'default_mrp_production_ids': self.ids,
            'default_fiscal_position_id': manufacturer.property_account_position_id.id,
        })

        return {
            'name': _(u"New account invoice from manufacturing orders"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        if 'location_dest_id' in vals:
            vals['manufacturer_id'] = self.env['stock.location'].browse(vals['location_dest_id']).partner_id.id
        return super(MrpProductionToInvoice, self).create(vals)
