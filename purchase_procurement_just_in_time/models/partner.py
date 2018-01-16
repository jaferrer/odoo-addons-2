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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See theEUCHNER FRANCE
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import datetime as dt

from dateutil.relativedelta import relativedelta

from openerp import models, fields, api

DOMAIN_PARTNER_ACTIVE_SCHEDULER = [('supplier', '=', True),
                                   ('nb_days_scheduler_frequency', '!=', False),
                                   ('nb_days_scheduler_frequency', '!=', 0),
                                   ('next_scheduler_date', '!=', False)]


class JitResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_default_order_group_period(self):
        order_group_period_id = self.env['ir.config_parameter'].\
            get_param('purchase_procurement_just_in_time.order_group_period')
        order_group_period_id = order_group_period_id and int(order_group_period_id) or False
        order_group_period = order_group_period_id and \
            self.env['procurement.time.frame'].browse(order_group_period_id) or self.env['procurement.time.frame']
        return order_group_period

    def _get_default_nb_max_draft_orders(self):
        return int(self.env['ir.config_parameter'].\
            get_param('purchase_procurement_just_in_time.nb_max_draft_orders') or 0)

    def _get_default_nb_days_scheduler_frequency(self):
        return int(self.env['ir.config_parameter'].\
            get_param('purchase_procurement_just_in_time.nb_days_scheduler_frequency') or 0)

    order_group_period = fields.Many2one('procurement.time.frame', string="Order grouping period",
                                         help="Select here the time frame by which orders line placed to this supplier"
                                              " should be grouped by PO. This is value should be set to the typical "
                                              "delay between two orders to this supplier.", track_visibility='onchange',
                                         default=_get_default_order_group_period)
    nb_max_draft_orders = fields.Integer(string="Maximal number of draft purchase orders",  track_visibility='onchange',
                                         help="Used by the purchase planner to generate draft orders",
                                         default=_get_default_nb_max_draft_orders)
    nb_days_scheduler_frequency = fields.Integer(string="Scheduler frequency (in days)", track_visibility='onchange',
                                                 default=_get_default_nb_days_scheduler_frequency)
    last_scheduler_date = fields.Datetime(string="Last scheduler date", readonly=True)
    next_scheduler_date = fields.Datetime(string="Next scheduler date")
    scheduler_sequence = fields.Integer(string="Sequence for purchase scheduler", track_visibility='onchange')

    @api.multi
    def get_nb_draft_orders(self):
        self.ensure_one()
        return len(self.env['purchase.order'].search([('partner_id', '=', self.id),
                                                      ('state', '=', 'draft'),
                                                      ('date_order', '!=', False),
                                                      ('date_order_max', '!=', False)]))

    @api.model
    def get_suppliers_to_launch(self):
        domain_partner = DOMAIN_PARTNER_ACTIVE_SCHEDULER + [('next_scheduler_date', '<=', fields.Datetime.now())]
        suppliers_to_launch = self.search(domain_partner)
        return suppliers_to_launch

    @api.model
    def launch_purchase_scheduler_by_supplier(self):
        suppliers_to_launch = self.get_suppliers_to_launch()
        for supplier in suppliers_to_launch:
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

    @api.multi
    def get_effective_order_group_period(self):
        self.ensure_one()
        order_group_period = self.order_group_period
        if not order_group_period:
            order_group_period_id = self.env['ir.config_parameter']. \
                get_param('purchase_procurement_just_in_time.order_group_period')
            if order_group_period_id:
                order_group_period = self.env['procurement.time.frame'].browse(int(order_group_period_id))
        return order_group_period

    @api.model
    def create(self, vals):
        if vals.get('nb_days_scheduler_frequency') and not vals.get('next_scheduler_date'):
            vals['next_scheduler_date'] = fields.Datetime.to_string(dt.now().replace(hour=22, minute=0, second=0))
        return super(JitResPartner, self).create(vals)
