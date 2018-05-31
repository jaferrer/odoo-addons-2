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


class PurchaseOrderDeleteReport(models.TransientModel):
    _name = 'purchase.order.delete.report'

    @api.model
    def delete_report(self):
        ir_value = self.env['ir.values'].search([('model', '=', 'purchase.order'), ('key2', '=', 'client_print_multi')])
        ir_value.unlink()

    @api.model
    def link_report_with_mail(self):
        report = self.env.ref(self._get_report_id())
        for xml_id in ['purchase.email_template_edi_purchase', 'purchase.email_template_edi_purchase_done']:
            mail_model = self.env.ref(xml_id)
            mail_model.report_template = report.id

    def _get_report_id(self):
        return 'purchase_order_report_aeroo.purchase_order_report_aeroo'


class PurchaseOrderPrint(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def print_quotation(self):
        super(PurchaseOrderPrint, self).print_quotation()
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, 'purchase.order.report.aeroo')
