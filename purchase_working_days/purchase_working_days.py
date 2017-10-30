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

from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import fields, models, api


class res_partner_with_calendar(models.Model):
    _inherit = "res.partner"

    resource_id = fields.Many2one("resource.resource", "Supplier resource",
                                  help="The supplier resource is used to define the working days of the supplier when "
                                       "calculating lead times. If undefined here the system will consider working "
                                       "days of the supplier being Monday to Friday.")
    partner_leaves_count = fields.Integer(string="Partner leaves", compute='_compute_supplier_leaves_count')

    @api.multi
    def schedule_working_days(self, nb_days, day_date):
        """Returns the date that is nb_days working days after day_date in the context of the current supplier.

        :param nb_days: int: The number of working days to add to day_date. If nb_days is negative, counting is done
                             backwards.
        :param day_date: datetime: The starting date for the scheduling calculation.
        :return: The scheduled date nb_days after (or before) day_date.
        :rtype : datetime
        """
        assert isinstance(day_date, datetime)
        if nb_days == 0:
            return day_date

        calendar = False
        resource = self.resource_id
        if resource:
            calendar = resource.calendar_id
        if not calendar:
            calendar = self.env.ref("resource_improved.default_calendar")

        newdate = calendar.schedule_days_get_date(nb_days, day_date=day_date,
                                                  resource_id=resource and resource.id or False,
                                                  compute_leaves=True)
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]
        return newdate

    @api.multi
    def _compute_supplier_leaves_count(self):
        for rec in self:
            supplier_leaves = rec.resource_id.leave_ids
            if supplier_leaves:
                rec.partner_leaves_count = len(supplier_leaves)
            else:
                rec.partner_leaves_count = 0


class purchase_order_line_working_days(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _get_date_planned(self, supplier_info, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.supplierinfo,
           when ordered at `date_order_str`.
           Overridden here to calculate with working days.

           :param browse_record | False supplier_info: product.supplierinfo, used to
               determine delivery delay (if False, default delay = 0)
           :param str date_order_str: date of order field, as a string in
               DEFAULT_SERVER_DATETIME_FORMAT
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = self.env.context.get('force_order_date',
                                          po.date_order if po else self.order_id.date_order)
        date_order = fields.Datetime.from_string(date_order)
        # We add one day to supplier dalay because day scheduling counts the first day
        if supplier_info:
            return supplier_info.name.schedule_working_days(int(supplier_info.delay) + 1, date_order)
        else:
            return date_order


class purchase_working_days(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _get_purchase_schedule_date(self):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement.
           Overriden here to calculate dates taking into account the applicable working days calendar of our warehouse
           or our company.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :rtype: datetime
           :return: the desired Schedule Date for the PO lines
        """
        do_not_save_result = self.env.context.get('do_not_save_result', False)
        proc_date = datetime.strptime(self.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        location = self.location_id or self.warehouse_id.view_location_id
        # If key 'do_not_save_result' in context of self, we transfer it to location's context.
        schedule_date = location.with_context(do_not_save_result=do_not_save_result). \
            schedule_working_days(-self.company_id.po_lead, proc_date)
        return schedule_date

    @api.multi
    def _get_purchase_order_date(self, schedule_date):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement.
           Overriden here to calculate dates taking into account the applicable working days calendar.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :param datetime schedule_date: desired Scheduled Date for the Purchase Order lines.
           :rtype: datetime
           :return: the desired Order Date for the PO
        """
        self.ensure_one()
        supplierinfos = self.product_id.seller_ids
        partner = supplierinfos and supplierinfos[0].name or self.env['res.partner']
        seller_delay = int(supplierinfos and supplierinfos[0].delay or 0.0)
        order_date = partner.schedule_working_days(-seller_delay, schedule_date)
        return order_date
