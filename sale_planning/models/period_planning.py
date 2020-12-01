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

from odoo import fields, models, api, _ as _t


class PeriodPlanning(models.Model):
    _inherit = 'period.planning'

    sale_planning_ids = fields.One2many('sale.planning', 'period_id', "Sale planning")
    sale_state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirm"),
        ('done', u"Done"),
    ], required=True, readonly=True, default='draft')
    count_sale_planning = fields.Integer(compute='_compute_sale_planning')
    count_completed_sale_planning = fields.Integer(compute='_compute_completed_sale_planning',
                                                   string="Completed sale planning")
    active = fields.Boolean("Is active", default=True)
    sale_group_id = fields.Many2one('procurement.group', string="Sale procurement group")

    @api.multi
    def _compute_sale_planning(self):
        for rec in self:
            rec.count_sale_planning = self.env['sale.planning'].search_count([('period_id', '=', rec.id)])

    @api.multi
    def _compute_completed_sale_planning(self):
        for rec in self:
            rec.count_completed_sale_planning = self.env['sale.planning'].search_count(
                [('period_id', '=', rec.id), '|', ('reserve_qty', '!=', 0), ('sale_qty', '!=', 0)])

    @api.multi
    @api.onchange('season_id', 'year_id')
    def _change_period(self):
        for rec in self:
            rec.period_warning = False
            res = self.env['period.planning'].search(
                [('season_id', '=', rec.season_id.id), ('year_id', '=', rec.year_id.id), ('active', '=', True)])
            if res:
                rec.period_warning = True

    @api.multi
    def see_sale_planning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Forecast',
            'res_model': 'sale.planning',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': self.env.context,
            'domain': [('period_id', '=', self.id)],
            'target': 'current',
        }

    @api.multi
    def see_planning_action(self):
        return self.get_formview_action()

    @api.multi
    def confirm_sale_planning(self):
        self.ensure_one()
        if self.purchase_state == 'confirm':
            view = self.env.ref('sale_planning.confirm_wizard')
            ctx = {'default_period_id': self.id}
            return {
                'name': 'Confirm?',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'confirm.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': ctx,
            }
        self.create_or_update_purchase_planning()

    @api.multi
    def add_product(self):
        view = self.env.ref('sale_planning.add_product_planning_wizard')
        ctx = {'default_period_id': self.id}
        return {
            'name': _t('Add product'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'add.product.planning.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def add_categ(self):
        view = self.env.ref('sale_planning.add_categ_planning_wizard')
        ctx = {'default_period_id': self.id}
        return {
            'name': _t('Add product'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'add.categ.planning.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def create_or_update_purchase_planning(self):
        self.ensure_one()
        # Récupération des lignes sale_planning correspondant à season + year
        # Méthode récursive où on créé une map <materiel, qté>
        dict_product = self._get_dict_product(self.sale_planning_ids)
        # Création des purchase_planning associé
        purchase_lines = self.env['purchase.planning'].search([('period_id', '=', self.id)])
        purchase_plannings = self.env['purchase.planning']
        for prod, dict_res in dict_product.items():
            line = purchase_lines.filtered(lambda r: r.product_id == prod)
            if line:
                # on update les quantités
                line.write({'suggest_qty_no_constraint': dict_res})
            else:
                purchase_plannings |= self.env['purchase.planning'].create({
                    'period_id': self.id,
                    'product_id': prod.id,
                    'supplier_id': prod.seller_ids[:1].id,
                    'suggest_qty_no_constraint': dict_res,
                })
        if self.purchase_state == 'confirm':
            self.cancel_po()
        # Changement de status des sale_planning de la periode
        self.sale_planning_ids.write({'state': 'confirm'})
        self.write({
            'sale_state': 'confirm',
            'purchase_state': 'draft',
        })
        # Redirection vers les lignes que l'on vient de créer
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Forecast',
            'res_model': 'purchase.planning',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': self.env.context,
            'domain': [('period_id', '=', self.id)],
        }

    @api.multi
    def merge_products(self, product_ids):
        self.ensure_one()
        products = [p for p in product_ids if p not in self.sale_planning_ids.mapped('product_id')]
        res = self.env['sale.planning'].create([{
            'period_id': self.id,
            'product_id': product.id,
            'state': 'draft',
            'categ_id': product.categ_id.id,
        } for product in products])
        return res

    @api.multi
    def merge_categ(self, categ_ids):
        self.ensure_one()
        categ_to_create = [x for x in categ_ids.ids if x not in self.category_ids.ids]
        list_categ_to_create = self.env['product.category'].browse(categ_to_create)
        product_domain = self.env['product.product']._get_products_for_sale_forecast()
        product_domain.append(('categ_id', 'in', list_categ_to_create.ids))
        products = self.env['product.product'].search(product_domain)
        self.merge_products(products)
        return self

    @api.model
    def _get_dict_product(self, sale_plannings):
        dict_product = {}
        for planning in sale_plannings:
            product_id = planning.product_id
            planning_quantity = planning.sale_qty + planning.reserve_qty
            if product_id.bom_ids:
                _, products = product_id.bom_ids[:1].recursive_explode(product_id, planning_quantity)
                for product, quantity in products:
                    dict_product.setdefault(product, 0)
                    dict_product[product] += quantity
            else:
                dict_product.setdefault(product_id, 0)
                dict_product[product_id] += planning_quantity
        return dict_product

    @api.multi
    def confirm_purchase_planning(self):
        self.ensure_one()
        super(PeriodPlanning, self).confirm_purchase_planning()
        # Récupération des sale_planning associées
        sale_plannings = self.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        season_date = self.season_id.display_name
        # Création des procurement_group
        group = self.env['procurement.group'].create({'name': season_date})
        year = self.year_id.name
        month = self.season_id.start_month_id.number
        date_start = date.today() + relativedelta(year=year, month=month, day=1)
        for planning in sale_plannings:
            product = planning.product_id
            stock_location = self.env.ref('stock.stock_location_stock')
            values = {
                'group_id': group,
                'date_planned': date_start,
                'user_id': self.env.user.id,
            }
            self.env['procurement.group'].run(product, planning.sale_qty, product.uom_id, stock_location,
                                              season_date, season_date, values)
            planning.write({'state': 'done'})
        # Changement de statut  des sale_planning
        self.sale_planning_ids.write({'state': 'done'})
        self.write({
            'sale_state': 'done',
            'sale_group_id': group.id,
        })

    @api.multi
    def cancel_po(self):
        self.ensure_one()
        super(PeriodPlanning, self).cancel_po()
        manufacturing_orders = self.env['mrp.production'].search(
            [('procurement_group_id', '=', self.sale_group_id.id), ('state', 'not in', ('cancel', 'done', 'progress'))])
        manufacturing_orders.action_cancel()


class PurchasePlanning(models.Model):
    _inherit = 'purchase.planning'

    sale_state = fields.Selection([
        ('draft', u"Draft"),
        ('confirm', u"Confirm"),
        ('done', u"Done"),
    ], related='period_id.sale_state', string="Sale state")
