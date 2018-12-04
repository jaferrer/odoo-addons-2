# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime as dt

from openerp import models, fields, api


class PurchaseOrderLineOverCover(models.Model):
    _inherit = 'purchase.order.line'

    coverage_to_approve = fields.Boolean(string=u"Coverage to approve", readonly=True)


class PurchaseOrderOverCover(models.Model):
    _inherit = 'purchase.order'

    coverage_to_approve = fields.Boolean(string=u"Coverage to approve", readonly=True)

    @api.multi
    def purchase_confirm(self):
        self.compute_coverage_state()
        nb_days_max_cover = int(self.env['ir.config_parameter'].
                                get_param('purchase_over_cover_validation.nb_days_max_cover') or 0)
        max_coverage_date = fields.Datetime.to_string(self.partner_id.schedule_working_days(nb_days_max_cover,
                                                                                            dt.today()))
        for rec in self:
            any_line_overcovered = False
            for line in rec.order_line:
                if not line.covering_date or line.covering_date and line.covering_date > max_coverage_date:
                    line.coverage_to_approve = True
                    any_line_overcovered = True
            if any_line_overcovered:
                rec.coverage_to_approve = True
            else:
                rec.signal_workflow('purchase_confirm')

    @api.multi
    def cover_validate(self):
        self.write({'coverage_to_approve': False})
        self.env['purchase.order.line'].search([('order_id', 'in', self.ids)]).write({'coverage_to_approve': False})
        self.signal_workflow('purchase_confirm')
