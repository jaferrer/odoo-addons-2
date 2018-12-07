# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api
from openerp.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    nb_picking_to_invoice = fields.Integer(string=u"Number of pickings to invoice",
                                           compute='_compute_nb_picking_to_invoice')
    is_service_to_invoice = fields.Boolean(string=u"Is at least one service to invoice",
                                           compute='_compute_is_service_to_invoice')

    @api.multi
    def _compute_nb_picking_to_invoice(self):
        for rec in self:
            rec.nb_picking_to_invoice = len(rec.get_pickings_to_invoice()) or 0

    @api.multi
    def _compute_is_service_to_invoice(self):
        for rec in self:
            rec.is_service_to_invoice = any([line.is_service_to_invoice for line in rec.order_line])

    @api.multi
    def get_pickings_to_invoice(self):
        self.ensure_one()
        return self.env['stock.picking'].search([('id', 'in', self.picking_ids.ids),
                                                 ('state', '=', 'done'),
                                                 ('invoice_state', '=', '2binvoiced')])

    @api.multi
    def create_invoice(self):
        self.ensure_one()
        action = self.env.ref('stock_account.action_stock_invoice_onshipping')
        result = action.read()[0]
        context = result.get('context', {})
        # Convert context from string to dict if needed
        if str(context) == context:
            context = eval(context)
        service_line_vals = self.is_service_to_invoice and [
            (0, 0, {'product_id': line.product_id and line.product_id.id or False,
                    'name': line.name,
                    'invoice_qty': line.remaining_invoice_qty,
                    'remaining_invoice_qty': line.remaining_invoice_qty,
                    'purchase_line_id': line.id}) for line in self.order_line if
            line.is_service_to_invoice] or False
        context['active_model'] = 'stock.picking'
        context['active_ids'] = self.get_pickings_to_invoice().ids
        context['default_display_remaining_services'] = self.is_service_to_invoice
        context['default_service_line_ids'] = service_line_vals
        context['invoice_purchase_order_id'] = self.id
        result['context'] = context
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    remaining_invoice_qty = fields.Float(string=u"Remaining quantity to invoice",
                                         compute='_compute_remaining_invoice_qty')
    is_service_to_invoice = fields.Boolean(string=u"Is a service to invoice", compute='_compute_is_service_to_invoice')

    @api.multi
    def _compute_remaining_invoice_qty(self):
        for rec in self:
            remaining_invoice_qty = rec.product_qty
            for line in rec.invoice_lines:
                if line.invoice_id.state != 'cancel':
                    remaining_invoice_qty -= line.uos_id and self.env['product.uom']. \
                        _compute_qty_obj(from_unit=line.uos_id,
                                         qty=line.quantity,
                                         to_unit=rec.product_uom) or line.product_qty
            rec.remaining_invoice_qty = remaining_invoice_qty

    @api.multi
    def _compute_is_service_to_invoice(self):
        for rec in self:
            rec.is_service_to_invoice = (rec.product_id.type == 'service' or not rec.product_id) and \
                                        float_compare(rec.remaining_invoice_qty, 0,
                                                      precision_rounding=rec.product_uom.rounding) > 0


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = 'stock.invoice.onshipping'

    display_remaining_services = fields.Boolean(string=u"Display remaining services on order", readonly=True)
    service_line_ids = fields.One2many('stock.invoice.onshipping.service.line', 'wizard_id',
                                       string=u"Service lines to invoice")

    @api.model
    def check_invoicable(self, active_ids, count):
        if not self.env.context.get('default_display_remaining_services'):
            return super(StockInvoiceOnshipping, self).check_invoicable(active_ids, count)

    @api.multi
    def get_not_null_service_line(self):
        self.ensure_one()
        result = self.env['stock.invoice.onshipping.service.line']
        for line in self.service_line_ids:
            if line.invoice_qty > 0.0001:
                result |= line
        return result

    @api.multi
    def create_invoice_for_service_lines(self):
        self.ensure_one()
        purchase_order_id = self.env.context.get('invoice_purchase_order_id')
        if not purchase_order_id:
            return False
        purchase_order = self.env['purchase.order'].search([('id', '=', purchase_order_id)])
        journal2type = {'sale': 'out_invoice', 'purchase': 'in_invoice', 'sale_refund': 'out_refund',
                        'purchase_refund': 'in_refund'}
        inv_type = journal2type.get(self.journal_type) or 'out_invoice'
        key = purchase_order.partner_id, purchase_order.currency_id.id, purchase_order.company_id.id, self.env.uid
        invoice_vals = self.env['stock.picking']. \
            with_context(date_inv=self.invoice_date). \
            _get_invoice_vals(key, inv_type, self.journal_id.id, move=self.env['stock.move'])
        invoice_vals['origin'] = purchase_order.name
        invoice = self.env['account.invoice'].create(invoice_vals)
        purchase_order.write({'invoice_ids': [(4, invoice.id)]})
        return invoice

    @api.multi
    def create_invoice(self):
        result = []
        for rec in self:
            invoice_ids = super(StockInvoiceOnshipping,
                                rec.with_context(no_invoice_creation_check=True)).create_invoice()
            result += invoice_ids
            not_null_service_lines = rec.get_not_null_service_line()
            if not not_null_service_lines:
                continue
            # Create invoice for service lines if needed
            invoice = invoice_ids and self.env['account.invoice'].search([('id', '=', invoice_ids[0])]) or \
                      rec.create_invoice_for_service_lines() or False
            if not invoice:
                continue
            if invoice.id not in result:
                result += [invoice.id]
            not_null_service_lines.create_invoice_lines_for_services(invoice)
        return result


class StockInvoiceOnshippingServiceLine(models.TransientModel):
    _name = 'stock.invoice.onshipping.service.line'

    wizard_id = fields.Many2one('stock.invoice.onshipping', string=u"Wizard", readonly=True)
    product_id = fields.Many2one('product.product', string=u"Product", readonly=True)
    name = fields.Char(string=u"Description", readonly=True)
    invoice_qty = fields.Float(string=u"Quantity to invoice")
    remaining_invoice_qty = fields.Float(string=u"Remaining quantity to invoice", readonly=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string=u"Purchase Order Line", readonly=True, required=True)

    @api.multi
    def create_invoice_lines_for_services(self, invoice):
        for rec in self:
            purchase_order_line = rec.purchase_line_id
            name = rec.name or rec.product_id.name or False
            account_id = self.env['purchase.order']._choose_account_from_po_line(purchase_order_line)
            invoice_line_vals = self.env['purchase.order']._prepare_inv_line(account_id, purchase_order_line)
            invoice_line_vals['quantity'] = rec.invoice_qty
            invoice_line_vals['invoice_id'] = invoice.id
            invoice_line_vals['origin'] = rec.purchase_line_id.order_id.name or name
            invoice_line = self.env['account.invoice.line'].create(invoice_line_vals)
            purchase_order_line.write({'invoice_lines': [(4, invoice_line.id)]})


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _create_invoice_line_from_vals(self, move, invoice_line_vals):
        return super(StockMove, self.with_context(do_not_create_line_for_services=True)). \
            _create_invoice_line_from_vals(move, invoice_line_vals)
