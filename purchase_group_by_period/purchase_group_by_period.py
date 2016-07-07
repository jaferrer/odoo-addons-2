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
from dateutil.relativedelta import relativedelta, MO, SU

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import fields, models, api, _


class res_partner_with_period(models.Model):
    _inherit = 'res.partner'

    order_group_period = fields.Many2one('procurement.time.frame', string="Order grouping period",
                                          help="Select here the time frame by which orders line placed to this supplier"
                                               " should be grouped by PO. This is value should be set to the typical "
                                               "delay between two orders to this supplier.")


class purchase_order_with_period(models.Model):
    _inherit = 'purchase.order'

    date_order_max = fields.Datetime("Maximum order date", compute="_compute_date_order_max", store=True,
                                     help="This is the latest date an order line inside this PO must be ordered. "
                                          "PO lines with an order date beyond this date must be grouped in a later PO. "
                                          "This date is set according to the supplier order_group_period and to this "
                                          "PO order date.")

    @api.depends('partner_id.order_group_period','date_order')
    def _compute_date_order_max(self):
        """Computes date_order_max field according to this order date_order and to the supplier order_group_period."""
        for rec in self:
            if rec.partner_id and rec.partner_id.order_group_period:
                date_order = datetime.strptime(rec.date_order, DEFAULT_SERVER_DATETIME_FORMAT)
                ds, date_order_max = rec.partner_id.order_group_period.get_start_end_dates(date_order)
                rec.date_order_max = date_order_max.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                rec.date_order_max = False


class procurement_time_frame(models.Model):
    _name = 'procurement.time.frame'

    name = fields.Char(required=True)
    nb = fields.Integer("Number")
    period_type = fields.Selection([('days',"Day(s)"),('weeks',"Week(s)"),('months',"Month(s)"),('years',"Year(s)")])

    def get_start_end_dates(self, date, date_ref = None):
        delta = 0
        if date_ref:
            ds_start, ds_end = self._get_interval(date_ref)
            delta = (date_ref - ds_start).days + 1

        real_start, real_end = self._get_interval(date - relativedelta(days=delta))

        real_start = real_start + relativedelta(days=delta)
        real_end = real_end + relativedelta(days=delta)

        return real_start, real_end

    def _get_interval(self, date):
        """Returns the start and end dates of the time frame including date.

                @param self: object pointer,
                @param date: datetime object,
                @return: A tuple of datetime objects."""
        if self.period_type == 'days':
            doy = date.timetuple().tm_yday
            date_start = date + relativedelta(days=-((doy - 1) % self.nb), hour=0, minute=0, second=0)
            date_end = date_start + relativedelta(days=self.nb - 1, hour=23, minute=59, second=59)
        elif self.period_type == 'weeks':
            woy = date.isocalendar()[1]
            date_start = date + relativedelta(weeks=-((woy - 1) % self.nb) - 1, days=1, weekday=MO,
                                              hour=0, minute=0, second=0)
            date_end = date_start + relativedelta(weeks=self.nb - 1, weekday=SU, hour=23, minute=59, second=59)
        elif self.period_type == 'months':
            month = date.month
            date_start = date + relativedelta(months=-((month - 1) % self.nb), day=1, hour=0, minute=0, second=1)
            date_end = date_start + relativedelta(months=self.nb - 1, day=31, hour=23, minute=59, second=59)
        elif self.period_type == 'years':
            year = date.year
            date_start = date + relativedelta(years=-((year - 1) % self.nb), month=1, day=1, hour=0, minute=0, second=1)
            date_end = date_start + relativedelta(years=self.nb - 1, month=12, day=31, hour=23, minute=59, second=59)
        # print "Date: %s, date_start: %s, date_end: %s, period_type: %s, nb: %s" % (date, date_start, date_end, self.period_type, self.nb)
        return date_start, date_end


class procurement_order_group_by_period(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def make_po(self):
        """ Resolve the purchase from procurement, which may result in a new PO creation, a new PO line creation or a
        quantity change on existing PO line.
        Note that some operations (as the PO creation) are made as SUPERUSER because the current user may not have
        rights to do it (mto product launched by a sale for example)
        Overridden here to take into account the supplier order grouping time frame.

        @return: dictionary giving for each procurement its related resolving PO line.
        """
        res = {}
        company = self.env.user.company_id
        po_obj = self.env['purchase.order']
        po_line_obj = self.env['purchase.order.line']
        seq_obj = self.env['ir.sequence']
        pass_ids = []
        linked_po_ids = []
        sum_po_line_ids = []
        for procurement in self:
            partner = self._get_product_supplier(procurement)
            if not partner or not partner.order_group_period:
                return super(procurement_order_group_by_period, self).make_po()
            else:
                schedule_date = self._get_purchase_schedule_date(procurement, company)
                purchase_date = self._get_purchase_order_date(procurement, company, schedule_date)
                line_vals = self._get_po_line_values_from_proc(procurement, partner, company, schedule_date)
                # look for any other draft PO for the same supplier, to attach the new line on instead of creating
                # a new draft one
                available_draft_po_ids = po_obj.search([('partner_id', '=', partner.id), ('state', '=', 'draft'),
                                        ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                                        ('location_id', '=', procurement.location_id.id),
                                        ('company_id', '=', procurement.company_id.id),
                                        ('dest_address_id', '=', procurement.partner_dest_id.id),
                                        ('date_order_max', '>=', purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                        ('date_order', '<=', purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))])
                if available_draft_po_ids:
                    po_rec = available_draft_po_ids[0]
                    #if the product has to be ordered earlier those in the existing PO, we replace the purchase date on the order to avoid ordering it too late
                    if datetime.strptime(po_rec.date_order, DEFAULT_SERVER_DATETIME_FORMAT) > purchase_date:
                        po_rec.date_order = purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    # look for any other PO line in the selected PO with same product and UoM to sum quantities instead
                    # of creating a new po line
                    available_po_line_ids = po_line_obj.search([('order_id', '=', po_rec.id),
                                                                ('product_id', '=', line_vals['product_id']),
                                                                ('product_uom', '=', line_vals['product_uom'])])
                    if available_po_line_ids:
                        po_line = available_po_line_ids[0]
                        po_line_id = po_line.id
                        new_qty, new_price = self._calc_new_qty_price(procurement, po_line=po_line)

                        if new_qty > po_line.product_qty:
                            po_line.write({'product_qty': new_qty, 'price_unit': new_price})
                            self.update_origin_po(po_line, procurement)
                            sum_po_line_ids.append(procurement)
                    else:
                        line_vals.update(order_id=po_rec.id)
                        po_line_id = po_line_obj.sudo().create(line_vals).id
                        linked_po_ids.append(procurement)
                else:
                    date_order, date_end = partner.order_group_period.get_start_end_dates(purchase_date)
                    name = seq_obj.next_by_code('purchase.order') or _('PO: %s') % procurement.name
                    po_vals = {
                        'name': name,
                        'origin': "%s - %s" % (date_order.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                               date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                        'partner_id': partner.id,
                        'location_id': procurement.location_id.id,
                        'picking_type_id': procurement.rule_id.picking_type_id.id,
                        'pricelist_id': partner.property_product_pricelist_purchase.id,
                        'currency_id': partner.property_product_pricelist_purchase and \
                                       partner.property_product_pricelist_purchase.currency_id.id or \
                                       procurement.company_id.currency_id.id,
                        'date_order': date_order.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': procurement.company_id.id,
                        'fiscal_position': partner.property_account_position and \
                                           partner.property_account_position.id or False,
                        'payment_term_id': partner.property_supplier_payment_term.id or False,
                        'dest_address_id': procurement.partner_dest_id.id,
                    }
                    po_id = self.sudo().create_procurement_purchase_order(procurement, po_vals, line_vals)
                    po_line_id = self.env['purchase.order'].browse(po_id).order_line[0].id
                    pass_ids.append(procurement)
                res[procurement.id] = po_line_id
                procurement.write({'purchase_line_id': po_line_id})
        for proc in pass_ids:
            proc.message_post(body=_("Draft Purchase Order created"))
        for proc in linked_po_ids:
            proc.message_post(body=_("Purchase line created and linked to an existing Purchase Order"))
        for proc in sum_po_line_ids:
            proc.message_post(body=_("Quantity added in existing Purchase Order Line"))
        return res
