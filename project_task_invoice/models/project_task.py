# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api, _ as _t
from odoo.exceptions import UserError


class ProjectTaskInvoice(models.Model):
    _inherit = 'project.task'

    saling_type = fields.Selection([
        ('manual', u"Manual"),
        ('with_coeff', u"With Factor"),
        ('equal_planned_days', u"Is planned Days"),
        ('free', u"Free"),
    ], u"Saling Type", default='manual', required=True)
    time_spent = fields.Float(u"Time sold")
    date_invoiced = fields.Date(u"Invoice Date")
    date_delivered = fields.Date(u"Date delivered", track_visibility='onchange', readonly=True)
    project_partner_id = fields.Many2one(
        'res.partner',
        u"Client du projet",
        related='project_id.partner_id',
        readonly=True
    )
    initial_sale_line_id = fields.Many2one(
        'sale.order.line',
        u"Sale Order Line",
        domain=[('order_id.state', '!=', 'cancel')]
    )
    product_to_invoice_id = fields.Many2one('product.product', u"Product To Invoice",
                                            related='category_id.product_to_invoice_id', readonly=True)
    initial_sale_id = fields.Many2one('sale.order', u"Sale Order")
    stage_is_delivered = fields.Boolean(u"Is Delivered", related='stage_id.is_delivered', store=True)
    must_be_invoiced = fields.Boolean(related='category_id.must_be_invoiced', store=True)

    coefficient_ids = fields.Many2many('project.task.coefficient', string=u"Factor")
    time_with_coefficient = fields.Float(string=u"Time with coefficient", compute='_compute_calculate_time')
    time_with_coefficient_rounded = fields.Float(string=u"Time with coefficient rounded",
                                                 compute="_compute_calculate_time")
    time_open = fields.Float(string=u"Manuel Supplement")
    time_free = fields.Float(string=u"Time free")
    time_free_comment = fields.Text(string=u"Comment about time free")
    estimated_time_customer = fields.Float(u"Duration", compute="_compute_estimated_time_customer", store=True)
    invoice_time = fields.Float(u"Duration To Invoice", compute="_compute_estimated_time_customer", store=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ProjectTaskInvoice, self).default_get(fields_list)
        if 'saling_type' in fields_list and res.get('project_id') and not self.env.context.get('default_saling_type'):
            res['saling_type'] = self.env['project.project'].browse(res.get('project_id')).saling_type
        return res

    @api.multi
    @api.depends('coefficient_ids', 'planned_days')
    def _compute_calculate_time(self):
        for rec in self:
            sum_coeff = reduce(lambda val, coeff: val * coeff.coefficient, rec.coefficient_ids,
                               rec.coefficient_ids and 1 or 0
                               )
            rec.time_with_coefficient = (rec.planned_days * sum_coeff)
            rec.time_with_coefficient_rounded = round((rec.planned_days * sum_coeff) * 4) / 4

    @api.multi
    @api.depends('saling_type', 'coefficient_ids', 'planned_days', 'time_open', 'time_spent', 'time_free')
    def _compute_estimated_time_customer(self):
        for rec in self:
            if rec.saling_type == 'with_coeff':
                rec.estimated_time_customer = rec.time_with_coefficient_rounded + rec.time_open
            elif rec.saling_type == 'manual':
                rec.estimated_time_customer = rec.time_spent
            elif rec.saling_type == 'free' or rec.saling_type == 'equal_planned_days':
                rec.estimated_time_customer = rec.planned_days
            rec.invoice_time = rec.saling_type != 'free' and rec.estimated_time_customer - rec.time_free or 0.0

    @api.onchange('initial_sale_line_id')
    def _onchange_initial_sale_line_id(self):
        self.initial_sale_id = self.initial_sale_line_id.order_id

    @api.onchange('initial_sale_id')
    def _onchange_initial_sale_id(self):
        if self.initial_sale_line_id.order_id != self.initial_sale_id:
            self.initial_sale_line_id = False

    @api.multi
    def action_mark_as_delivered(self):
        for rec in self:
            if rec.initial_sale_line_id:
                rec.initial_sale_line_id.qty_delivered += rec.time_spent
            if not rec.date_delivered:
                rec.date_delivered = fields.Date.today()

    @api.multi
    def action_cancel_delivery(self):
        for rec in self:
            if rec.initial_sale_line_id:
                rec.initial_sale_line_id.qty_delivered -= rec.time_spent
            rec.date_delivered = False

    @api.multi
    def invoice_project_task(self):
        if any(not rec.project_partner_id for rec in self):
            raise UserError(_t(u"You can't create an invoice from a task if the task's customer isn't filled"))
        if len(self.mapped('project_partner_id')) > 1:
            raise UserError(_t(u"You can't create an invoice for several customers"))
        return {
            'type': 'ir.actions.act_window',
            'name': 'To Invoice Tasks',
            'res_model': 'invoice.project.task.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    @api.multi
    def _prepare_invoice_line(self, qty=None):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        product = self.product_to_invoice_id or self.env.ref('project_task_invoice.ndp_product_product_other')
        account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(
                _t('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (product.name, product.id, product.categ_id.name))

        return {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.name,
            'account_id': account.id,
            'price_unit': product.with_context(
                partner_id=self.project_partner_id.id,
                pricelist=self.project_partner_id.property_product_pricelist.id
            ).price,
            'quantity': qty or self.invoice_time,
            'uom_id': product.uom_id.id,
            'product_id': product.id,
            'invoice_line_tax_ids': [(6, 0, product.taxes_id.ids)],
            'account_analytic_id': self.project_id.analytic_account_id.id,
        }
