# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api


class PeriodPlanning(models.Model):
    _name = 'period.planning'
    _description = "Period Planning"
    _order = 'year_id, season_id'

    name = fields.Char("Name")
    season_id = fields.Many2one('res.calendar.season', u"Season", required=True)
    year_id = fields.Many2one('res.calendar.year', u"Year", required=True)
    purchase_planning_ids = fields.One2many('purchase.planning', 'period_id', "Purchase planning")
    purchase_state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirmed"),
        ('lock', u"Locked"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')
    count_purchase_planning = fields.Integer(compute='_compute_purchase_planning')
    category_ids = fields.Many2many('product.category', string="Product Category")
    period_warning = fields.Boolean("Period warning")
    count_completed_purchase_planning = fields.Integer(compute='_compute_completed_purchase_planning',
                                                       string="Purchase planning done")
    purchase_group_id = fields.Many2one('procurement.group', string="Purchase procurement group")

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = rec.season_id.name + " " + str(rec.year_id.name)
            if rec.name:
                name = rec.name + " (" + name + ")"
            res.append((rec.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = args or []
        domain += ["|", ("season_id.name", operator, name), ("year_id.name", operator, name)]
        return self.search(domain, limit=limit).name_get()

    @api.multi
    def _compute_purchase_planning(self):
        for rec in self:
            rec.count_purchase_planning = self.env['purchase.planning'].search_count([('period_id', '=', rec.id)]) or 0

    @api.multi
    def _compute_completed_purchase_planning(self):
        for rec in self:
            rec.count_completed_purchase_planning = self.env['purchase.planning'].search_count(
                [('period_id', '=', rec.id), ('retained_qty', '!=', 0)]) or 0

    @api.multi
    def see_purchase_planning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Forecast',
            'res_model': 'purchase.planning',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': self.env.context,
            'domain': [('period_id', '=', self.id)],
            'target': 'current',
        }

    @api.multi
    def confirm_purchase_planning(self):
        self.ensure_one()
        # Récupération des lignes purchase_planning correspondant à season + year
        # Création d'une liste si retained_qty > 0
        purchase_plannings = self.purchase_planning_ids.filtered(lambda r: (r.retained_qty > 0))
        season_date = self.season_id.display_name
        # Création des procurement_group
        group = self.env['procurement.group'].create({'name': season_date})
        year = self.year_id.name
        month = self.season_id.start_month_id.number
        date_start = date.today() + relativedelta(year=year, month=month, day=1)
        for planning in purchase_plannings:
            product = planning.product_id
            stock_location = self.env.ref('stock.stock_location_stock')
            values = {
                'group_id': group,
                'date_planned': date_start,
                'user_id': self.env.user.id,
            }
            self.env['procurement.group'].run(product, planning.retained_qty, product.uom_id, stock_location,
                                              season_date, season_date, values)
        # Changement de statut des purchase_planning
        self.purchase_planning_ids.write({'state': 'confirm'})
        self.write({
            'purchase_state': 'confirm',
            'purchase_group_id': group.id,
        })

    @api.multi
    def compute_state(self):
        if not self:
            return
        purchase_states = self.env['purchase.order'].search([('group_id', '=', self.purchase_group_id.id)]).mapped(
            'state')
        if 'purchase' in purchase_states:
            self.purchase_state = 'lock'
            self.purchase_planning_ids.write({'state': 'lock'})
        else:
            self.purchase_state = 'confirm'
            self.purchase_planning_ids.write({'state': 'confirm'})
        if all(state in ('purchase', 'done', 'cancel') for state in purchase_states):
            self.purchase_state = 'done'
            self.purchase_planning_ids.write({'state': 'done'})

    @api.multi
    def cancel_po(self):
        self.ensure_one()
        purchase_orders = self.env['purchase.order'].search(
            [('group_id', '=', self.purchase_group_id.id), ('state', 'not in', ('cancel', 'done', 'purchase'))])
        purchase_orders.button_cancel()
        self.write({'purchase_state': 'draft'})
