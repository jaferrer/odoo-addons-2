# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            self.action_invoice_create_other_method(sale_orders)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_invoice_create_other_method(self, sale_orders):
        self._create_deposit_product_if_needed()
        invoices_by_so = {sale_order.id: self.env['account.invoice'] for sale_order in sale_orders}
        for order in sale_orders:
            amount = self._get_amount(order)
            self._check_deposit_product_is_valid()
            taxes = self._get_taxes(order)
            sol_datas = self.with_context(lang=order.partner_id.lang). \
                _populate_advance_payment_sale_order_line(order, amount, taxes)
            so_lines = self.env['sale.order.line']
            for sol_data in sol_datas:
                sol_data['order_id'] = order.id
                so_lines |= self.env['sale.order.line'].create(sol_data)
            invoices_by_so[order.id] = self._create_invoice(order, so_lines, amount)
        return invoices_by_so

    @api.multi
    def _create_invoice(self, order, so_lines, amount):
        """The param amount is un used because to set the account.invoice.line#price_unit
        we take the price_unit of the sale.order.line but we need to keep the compatibility"""
        account = self._find_account(order)
        if not account:
            raise UserError(_('There is no income account defined for this product: "%s".'
                              ' You may have to install a chart of account from Accounting app, settings menu.') %
                            self.product_id.name)

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        name = self.with_context(lang=order.partner_id.lang)._get_name()
        data_invoice = self._populate_invoice_advance_payment(order)
        data_invoice_lines = []
        for so_line in so_lines:
            data_invoice_lines.append(self._populate_invoice_advance_payment_line(
                account=account,
                name=name,
                order=order,
                so_lines=so_line
            ))
        invoice = self.env['account.invoice'].create(data_invoice)
        for data_invoice_line in data_invoice_lines:
            data_invoice_line["invoice_id"] = invoice.id
            self.env['account.invoice.line'].create(data_invoice_line)
        invoice.with_context(round=False).compute_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                                       values={'self': invoice, 'origin': order},
                                       subtype_id=self.env.ref('mail.mt_note').id)
        return invoice

    @api.multi
    def _populate_invoice_advance_payment(self, order):
        return {
            'name': order.client_order_ref or order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'team_id': order.team_id.id,
            'user_id': order.user_id.id,
            'comment': order.note,
        }

    @api.multi
    def _populate_invoice_advance_payment_line(self, account, name, order, so_lines=None):
        invoice_line_data = {
            'name': name,
            'origin': order.name,
            'account_id': account,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': self.product_id.uom_id.id,
            'product_id': self.product_id.id,
            'account_analytic_id': order.project_id.id or False,
        }
        if so_lines:
            invoice_line_data.update({
                'price_unit': sum([so_line.price_unit for so_line in so_lines]),
                'sale_line_ids': [(6, 0, so_lines.ids)],
                'invoice_line_tax_ids': [(6, 0, self._get_taxes(order, so_lines.mapped('tax_id')).ids)],
            })

        return invoice_line_data

    @api.multi
    def _get_taxes(self, order, taxes=None):
        taxes = taxes or self.product_id.taxes_id.filtered(lambda r: not order.company_id or
                                                           r.company_id == order.company_id)
        if order.fiscal_position_id and taxes:
            taxes = order.fiscal_position_id.map_tax(taxes)
        return taxes

    @api.multi
    def _get_name(self):
        name = _('Down Payment')
        if self.advance_payment_method == 'percentage':
            name = _("Down payment of %s%%") % (self.amount,)
        return name

    @api.multi
    def _get_amount(self, order):
        """Return the amount of the wizard or a percentage of the amount untaxed of the sale order"""
        amount = self.amount
        if self.advance_payment_method == 'percentage':
            amount = order.amount_untaxed * self.amount / 100
        return amount

    @api.multi
    def _find_account(self, order):
        self.ensure_one()
        account_id = False
        if self.product_id:
            account_id = self.product_id.property_account_income_id.id or \
                self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = self.env['ir.property'].get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        return account_id

    @api.multi
    def _check_deposit_product_is_valid(self):
        if self.product_id.invoice_policy != 'order':
            raise UserError(
                _('The product used to invoice a down payment should have an '
                  'invoice policy set to "Ordered quantities". '
                  'Please update your deposit product to be able to create a deposit invoice.'))
        if self.product_id.type != 'service':
            raise UserError(_("The product used to invoice a down payment should be of type 'Service'. "
                              "Please use another product or update this product."))

    @api.multi
    def _create_deposit_product_if_needed(self):
        if not self.product_id:
            vals = self._prepare_deposit_product()
            self.product_id = self.env['product.product'].create(vals)
            self.env['ir.values'].sudo().set_default('sale.config.settings',
                                                     'deposit_product_id_setting', self.product_id.id)

    @api.multi
    def _populate_advance_payment_sale_order_line(self, order, amount, taxes):
        return [{
            'name': _('Advance: %s') % (time.strftime('%m %Y'),),
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'discount': 0.0,
            'product_uom': self.product_id.uom_id.id,
            'product_id': self.product_id.id,
            'tax_id': [(6, 0, taxes.ids)],
        }]

    def _prepare_deposit_product(self):
        return {
            'name': 'Down payment',
            'type': 'service',
            'invoice_policy': 'order',
            'property_account_income_id': self.deposit_account_id.id,
            'taxes_id': [(6, 0, self.deposit_taxes_id.ids)],
        }
