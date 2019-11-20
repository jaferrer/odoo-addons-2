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
    def link_report_with_mail(self):
        """
        Replace the Odoo report by the aeroo report in the 'Send by mail' button of the form view.
        """

        mail_model = self.env.ref('purchase.email_template_edi_purchase')
        report = self.env.ref(self._get_report_id())
        mail_model.report_template = report.id

    @api.model
    def _get_report_id(self):
        return 'purchase_order_report_aeroo.purchase_order_report_aeroo'

    @api.model
    def hide_odoo_report(self):
        """
        Get rid of the Odoo report in the list of the 'Print' action.
        """

        odoo_purchase_order_report = self.env.ref('purchase.action_report_purchase_order')
        odoo_purchase_quotation_report = self.env.ref('purchase.report_purchase_quotation')
        self.env['ir.actions.report'].browse(odoo_purchase_order_report.id).unlink_action()
        self.env['ir.actions.report'].browse(odoo_purchase_quotation_report.id).unlink_action()


class PurchaseOrderReportAeroo(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def print_quotation(self):
        """
        Replace the Odoo report form view by the aeroo report in the 'Print' button of the form view.
        """
        return self.env.ref('purchase_order_report_aeroo.purchase_order_report_aeroo').report_action(self, config=False)
