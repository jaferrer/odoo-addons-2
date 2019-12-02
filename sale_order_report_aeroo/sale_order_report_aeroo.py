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
    def link_report_with_mail(self):
        """
        Replace the Odoo report by the aeroo report in the 'Send by mail' button of the form view.
        """

        mail_model = self.env.ref('sale.email_template_edi_sale')
        report = self.env.ref(self._get_report_id())
        mail_model.report_template = report.id

    @api.model
    def _get_report_id(self):
        return 'sale_order_report_aeroo.sale_order_report_aeroo'

    @api.model
    def hide_odoo_report(self):
        """
        Get rid of the Odoo report in the list of the 'Print' action.
        """

        odoo_sale_order_report = self.env.ref('sale.action_report_saleorder')
        self.env['ir.actions.report'].browse(odoo_sale_order_report.id).unlink_action()


class SaleOrderReportAeroo(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def multi_reports_print_quotation(self, report_xml_id):
        """
        In case there are several reports for 'sale.order'.
        """
        return self.env.ref(report_xml_id).report_action(self, config=False)

    @api.multi
    def print_quotation(self):
        """
        Replace the Odoo report form view by the aeroo report in the 'Print' button of the form view.
        """
        return self.env.ref('purchase_order_report_aeroo.purchase_order_report_aeroo').report_action(self, config=False)
