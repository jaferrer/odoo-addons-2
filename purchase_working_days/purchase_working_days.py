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


class purchase_order_line_working_days(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _get_date_planned(self, supplier_info, date_order_str):
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
        order_date = datetime.strptime(date_order_str, DEFAULT_SERVER_DATETIME_FORMAT)
        # We add one day to supplier dalay because day scheduling counts the first day
        supplier_delay = int(supplier_info.delay) + 1 if supplier_info else 0
        if supplier_delay == 0:
            return order_date

        calendar_id = False
        supplier_id = supplier_info.name
        resource_id = supplier_id and supplier_id.resource_id or False
        if resource_id:
            calendar_id = supplier_id.resource_id.calendar_id
        if not calendar_id:
            calendar_id = self.env.ref("stock_working_days.default_calendar")

        newdate = calendar_id.schedule_days_get_date(supplier_delay, day_date=order_date,
                                                      resource_id=resource_id and resource_id.id or False,
                                                      compute_leaves=True)
        # For some reason call with new api returns a list of 1 date instead of the date
        if isinstance(newdate, (list, tuple)):
            newdate = newdate[0]
        return newdate


class purchase_working_days(models.Model):
    _inherit = "procurement.order"

    def _get_supplier_calendar(self):
        """Returns the applicable (calendar, resource) tuple to use for calculating supplier lead times.
        The applicable calendar is the calendar of the resource defined for this supplier or the module's default
        calendar which considers workings days as being Monday to Friday.
        The applicable resource if the supplier's resource if defined."""
        calendar_id = False
        supplier_id = self._get_product_supplier(self)
        resource_id = supplier_id and supplier_id.resource_id or False
        if resource_id:
            calendar_id = supplier_id.resource_id.calendar_id
        if not calendar_id:
            calendar_id = self.env.ref("stock_working_days.default_calendar")
        return calendar_id, resource_id

    @api.model
    def _get_purchase_schedule_date(self, procurement, company):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement.
           Overriden here to calculate dates taking into account the applicable working days calendar of our warehouse
           or our company.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :rtype: datetime
           :return: the desired Schedule Date for the PO lines
        """
        calendar_id, resource_id = procurement._get_move_calendar()
        proc_date = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        schedule_date = procurement._schedule_working_days(-company.po_lead, proc_date, resource_id, calendar_id)
        return schedule_date

    @api.model
    def _get_purchase_order_date(self, procurement, company, schedule_date):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement.
           Overriden here to calculate dates taking into account the applicable working days calendar.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :param datetime schedule_date: desired Scheduled Date for the Purchase Order lines.
           :rtype: datetime
           :return: the desired Order Date for the PO
        """
        calendar_id, resource_id = procurement._get_supplier_calendar()
        seller_delay = int(procurement.product_id.seller_delay)
        order_date = procurement._schedule_working_days(-seller_delay, schedule_date, resource_id, calendar_id)
        return order_date


