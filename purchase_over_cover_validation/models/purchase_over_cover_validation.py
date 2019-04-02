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

from openerp import models, fields, api


class PurchaseOrderLineOverCover(models.Model):
    _inherit = 'purchase.order.line'

    coverage_to_approve = fields.Boolean(string=u"Coverage to approve", readonly=True)

    @api.multi
    def compute_coverage_state(self):
        result = super(PurchaseOrderLineOverCover, self).compute_coverage_state()
        if not self.env.context.get('do_not_update_coverage_data'):
            orders = self.env['purchase.order']
            draft_orders = self.env['purchase.order']
            for rec in self:
                orders |= rec.order_id
                if rec.order_id.state == 'draft':
                    draft_orders |= rec.order_id
            orders.reset_coverage_data()
            draft_orders.update_coverage_data()
        return result


class PurchaseOrderOverCover(models.Model):
    _inherit = 'purchase.order'

    coverage_to_approve = fields.Boolean(string=u"Coverage to approve", readonly=True)

    @api.multi
    def update_coverage_data(self, confirm_is_possible=False):
        nb_days_max_cover = int(self.env['ir.config_parameter'].
                                get_param('purchase_over_cover_validation.nb_days_max_cover') or 0)
        for rec in self:
            any_line_over_covered = False
            for line in rec.order_line:
                pol_requested_date = fields.Datetime.from_string(line.requested_date)
                pol_covering_date = fields.Datetime.from_string(line.covering_date) if line.covering_date else False
                date_coverage_max = rec.location_id.schedule_working_days(nb_days_max_cover, pol_requested_date)
                if not pol_covering_date or pol_covering_date and pol_covering_date > date_coverage_max:
                    any_line_over_covered = True
                    if not line.coverage_to_approve:
                        line.coverage_to_approve = True
            if any_line_over_covered and not rec.coverage_to_approve:
                rec.coverage_to_approve = True
            elif confirm_is_possible:
                rec.signal_workflow('purchase_confirm')

    @api.multi
    def purchase_confirm(self):
        """ purchase order needs hierarchical validation if stock qty needed in the futures days
        covered by products in stock (including current purchase order) do not exceed 'nb_days_max_cover' """

        self.compute_coverage_state()
        self.update_coverage_data(confirm_is_possible=True)

    @api.multi
    def reset_coverage_data(self):
        self.search([('coverage_to_approve', '=', True)]).write({'coverage_to_approve': False})
        self.env['purchase.order.line'].search([('order_id', 'in', self.ids),
                                                ('coverage_to_approve', '=', True)]).write({'coverage_to_approve': False})

    @api.multi
    def action_cancel(self):
        result = super(PurchaseOrderOverCover, self).action_cancel()
        self.reset_coverage_data()
        return result

    @api.multi
    def cover_validate(self):
        self.write({'coverage_to_approve': False})
        self.env['purchase.order.line'].search([('order_id', 'in', self.ids)]).write({'coverage_to_approve': False})
        self.signal_workflow('purchase_confirm')
