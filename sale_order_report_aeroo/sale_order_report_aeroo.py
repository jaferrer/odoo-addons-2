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

from odoo import models, api


class SaleOrderDeleteReport(models.TransientModel):
    _name = 'sale.order.delete.report'

    @api.model
    def delete_report(self):
        existing_report = self.env.ref('sale.report_sale_order')
        ir_value = self.env['ir.values']. \
            search([('value', '=', 'ir.actions.report.xml,' + unicode(existing_report.id))])
        ir_value.unlink()

    @api.model
    def link_report_with_mail(self):
        try:
            mail_model = self.env.ref('sale.email_template_edi_sale')
            report = self.env.ref(self._get_report_id())
            mail_model.report_template = report.id
        except ValueError:
            pass

    def _get_report_id(self):
        return 'sale_order_report_aeroo.sale_order_report_aeroo'


class SaleOrderPrint(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def print_quotation(self):
        super(SaleOrderPrint, self).print_quotation()
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, 'sale.order.report.aeroo')
