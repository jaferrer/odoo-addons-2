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

from datetime import datetime as dt

from dateutil.relativedelta import relativedelta

from openerp import models, fields, api


class JitResPartner(models.Model):
    _inherit = 'res.partner'

    order_group_period = fields.Many2one('procurement.time.frame', string="Order grouping period",
                                         help="Select here the time frame by which orders line placed to this supplier"
                                              " should be grouped by PO. This is value should be set to the typical "
                                              "delay between two orders to this supplier.")
    nb_max_draft_orders = fields.Integer(string="Maximal number of draft purchase orders",
                                         help="Used by the purchase planner to generate draft orders")
    nb_days_scheduler_frequency = fields.Integer(string="Scheduler frequency (in days)")
    last_scheduler_date = fields.Datetime(string="Last scheduler date", readonly=True)
    next_scheduler_date = fields.Datetime(string="Next scheduler date")
    scheduler_sequence = fields.Integer(string="Sequence for purchase scheduler")

    @api.multi
    def get_nb_draft_orders(self):
        self.ensure_one()
        return len(self.env['purchase.order'].search([('partner_id', '=', self.id),
                                                      ('state', '=', 'draft'),
                                                      ('date_order', '!=', False),
                                                      ('date_order_max', '!=', False)]))

    @api.model
    def launch_purchase_scheduler_by_supplier(self):
        suppliers_to_check = self.search([('supplier', '=', True),
                                          ('nb_days_scheduler_frequency', '!=', False),
                                          ('next_scheduler_date', '!=', False)])
        suppliers_to_launch = self.env['res.partner']
        for supplier in suppliers_to_check:
            if supplier.next_scheduler_date and supplier.next_scheduler_date <= fields.Datetime.now():
                suppliers_to_launch |= supplier
                next_scheduler_date = fields.Datetime.from_string(supplier.next_scheduler_date)
                while next_scheduler_date <= dt.now():
                    next_scheduler_date += relativedelta(days=supplier.nb_days_scheduler_frequency)
                supplier.write({'next_scheduler_date': fields.Datetime.to_string(next_scheduler_date),
                                'last_scheduler_date': fields.Datetime.now()})
        if suppliers_to_launch:
            wizard = self.env['launch.purchase.planner'].create({
                'compute_all': False,
                'supplier_ids': [(6, 0, suppliers_to_launch.ids)]
            })
            wizard.procure_calculation()
