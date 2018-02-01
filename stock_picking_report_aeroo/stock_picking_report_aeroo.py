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


class AccountInvoiceDeleteReport(models.TransientModel):
    _name = 'stock.picking.delete.report'

    @api.model
    def delete_report(self):
        existing_report = self.env.ref('stock.action_report_delivery')
        ir_value = self.env['ir.values']. \
            search([('value', '=', 'ir.actions.report.xml,' + unicode(existing_report.id))])
        ir_value.unlink()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_print_picking(self):
        super(StockPicking, self).do_print_picking()
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, 'stock_picking_report_aeroo')
