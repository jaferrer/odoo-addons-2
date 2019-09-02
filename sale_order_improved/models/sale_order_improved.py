# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, api
from odoo.osv import expression


class SaleOrderImproved(models.Model):
    _inherit = 'sale.order'

    @api.multi
    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced(self):
        """
        Divise cette méthode en plusieurs blocs.
        Cf ligne 43 dans odoo -> addons -> sale -> models -> sale.py
        """

        line_invoice_status_all = self._get_invoice_lines_status()

        for rec in self:

            invoice_ids, refund_ids = rec._get_invoice_refund_and_cancelled()

            invoice_status = rec._compute_sale_order_invoice_status(line_invoice_status_all)

            rec.update({
                'invoice_count': len(set(invoice_ids.ids + refund_ids.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids,
                'invoice_status': invoice_status
            })

    def _get_invoice_lines_status(self):

        # Ignore the status of the deposit product
        deposit_product_id = self.env['sale.advance.payment.inv']._default_product_id()
        line_invoice_status_all = [(d['order_id'][0], d['invoice_status']) for d in
                                   self.env['sale.order.line'].read_group(
                                       self._get_invoice_lines_status_domain(deposit_product_id),
                                       ['order_id', 'invoice_status'], ['order_id', 'invoice_status'], lazy=False)]
        return line_invoice_status_all

    def _get_invoice_lines_status_domain(self, deposit_product_id):

        return [('order_id', 'in', self.ids), ('product_id', '!=', deposit_product_id.id)]

    def _get_invoice_refund_and_cancelled(self):

        self.ensure_one()
        invoice_ids = self.order_line.mapped('invoice_lines').mapped('invoice_id').filtered(
            lambda r: r.type in ['out_invoice', 'out_refund'])
        # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
        # 'account.invoice.refund')
        # use like as origin may contains multiple references (e.g. 'SO01, SO02')
        refunds = invoice_ids.search([('origin', 'like', self.name), ('company_id', '=', self.company_id.id),
                                      ('type', 'in', ('out_invoice', 'out_refund'))])
        invoice_ids |= refunds.filtered(lambda r: self.name in [origin.strip() for origin in r.origin.split(',')])

        # Search for refunds as well
        domain_inv = expression.OR([
            ['&', ('origin', '=', inv.number), ('journal_id', '=', inv.journal_id.id)]
            for inv in invoice_ids if inv.number
        ])
        if domain_inv:
            refund_ids = self.env['account.invoice'].search(expression.AND([
                ['&', ('type', '=', 'out_refund'), ('origin', '!=', False)],
                domain_inv
            ]))
        else:
            refund_ids = self.env['account.invoice'].browse()

        return invoice_ids, refund_ids

    def _compute_sale_order_invoice_status(self, line_invoice_status_all):

        self.ensure_one()
        line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == self.id]

        if self.state not in ('sale', 'done'):
            invoice_status = 'no'
        elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
            invoice_status = 'to invoice'
        elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
            invoice_status = 'invoiced'
        elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
            invoice_status = 'upselling'
        else:
            invoice_status = 'no'

        return invoice_status
