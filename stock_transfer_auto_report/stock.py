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

from openerp import models, fields, api


class AutoReportPickingType(models.Model):
    _inherit = 'stock.picking.type'

    report_id = fields.Many2one('ir.actions.report.xml', domain=[('model', '=', 'stock.picking')],
                                string="Report launched after transfer")


class AutoReportTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.multi
    def do_detailed_transfer_multi(self):
        self.ensure_one()
        result = self.do_detailed_transfer()
        report = self.picking_id.picking_type_id.report_id
        if report:
            return self.env['report'].with_context(active_ids=[self.picking_id.id]).get_action(
                self.picking_id, report.report_name)
        return result
