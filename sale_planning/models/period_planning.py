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
    merge_sale_planning = fields.Boolean("Merge")
    merge_sale_period_id = fields.Many2one('period.planning', "Sale Planning")
    count_product = fields.Integer("Product count", readonly=1, compute='_count_product')

    @api.multi
    def _compute_sale_planning(self):
        for rec in self:
            rec.count_sale_planning = self.env['sale.planning'].search_count([('period_id', '=', rec.id)])

    @api.multi
    def _compute_completed_sale_planning(self):
        for rec in self:
            rec.count_completed_sale_planning = self.env['sale.planning'].search_count(
                [('period_id', '=', rec.id), '|', ('reserve_qty', '!=', 0), ('sale_qty', '!=', 0)])

    @api.onchange('period_warning')
    def on_change_period_warning(self):
        for rec in self:
            if rec.period_warning:
                return {'domain': {
                    'merge_sale_period_id': [('season_id', '=', rec.season_id.id), ('year_id', '=', rec.year_id.id)]}}

    @api.onchange('season_id', 'year_id', 'category_ids')
    def _change_period(self):
        for rec in self:
            list_cat = self._get_all_category(rec.category_ids)
            rec.category_ids = [(6, 0, list_cat)]
            rec._count_product()
            rec.period_warning = False
            res = self.env['period.planning'].search(
                [('season_id', '=', rec.season_id.id), ('year_id', '=', rec.year_id.id)])
            if res:
                rec.period_warning = True

    @api.model
    def _count_product(self):
        product_domain = self.env['product.product']._get_products_for_sale_forecast(self.category_ids)
        product_domain.append(('categ_id', 'in', self.category_ids.ids))
        self.count_product = self.env['product.product'].search_count(product_domain)

    @api.model
    def _get_all_category(self, list_categ):
        res = []
        for categ in list_categ:
            res += self._get_child_categ(categ)
        res = [item for sublist in [res] for item in sublist]
        return list(set(res))

    @api.model
    def _get_child_categ(self, categ):
        res = [categ.id]
        if categ.child_id:
            for child in categ.child_id:
                res += self._get_child_categ(child)
            res = [item for sublist in [res] for item in sublist]
        return res

    @api.model
    def create(self, vals):
        if vals.get('merge_sale_planning'):
            planning_to_merge = self.env['period.planning'].browse(vals.get('merge_sale_period_id'))
            # Ajout des catégories manquantes
            [[_, _, list_categ]] = vals.get('category_ids')
            categ_to_create = [x for x in list_categ if x not in planning_to_merge.category_ids.ids]
            list_categ_to_create = self.env['product.category'].browse(categ_to_create)
            # products = self.env['product.product']._get_products_for_sale_forecast(list_categ_to_create)
            product_domain = self.env['product.product']._get_products_for_sale_forecast(list_categ_to_create)
            product_domain.append(('categ_id', 'in', list_categ_to_create.ids))
            products = self.env['product.product'].search(product_domain)
            self.env['sale.planning'].create([{
                'period_id': planning_to_merge.id,
                'product_id': product.id,
                'state': 'draft',
                'categ_id': product.categ_id.id,
            } for product in products])
            planning_to_merge.write({'category_ids': [(4, c.id) for c in list_categ_to_create]})
            return planning_to_merge
        res = super(PeriodPlanning, self).create(vals)
        product_domain = self.env['product.product']._get_products_for_sale_forecast(res.category_ids)
        product_domain.append(('categ_id', 'in', res.category_ids.ids))
        products = self.env['product.product'].search(product_domain)
        self.env['sale.planning'].create([{
            'period_id': res.id,
            'product_id': product.id,
            'state': 'draft',
            'categ_id': product.categ_id.id,
        } for product in products])
        return res

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
    def see_product(self):
        self.ensure_one()
        products = self.sale_planning_ids.mapped('product_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Forecast Products',
            'res_model': 'product.product',
            'view_type': 'form',
            'view_mode': 'form',
            'context': self.env.context,
            'domain': [('id', 'in', products.ids)],
            'target': 'current',
        }

    @api.multi
    def confirm_sale_planning(self):
        self.ensure_one()
        # On vérifie si un/ou plusieurs purchase planning existe déjà pour cette période, si oui on propose une fusion
        period_plannings = self.env['period.planning'].search(
            [('season_id', '=', self.season_id.id), ('year_id', '=', self.year_id.id),
             ('purchase_state', '=', 'draft')])
        purchase_plannings = self.env['purchase.planning'].search([('period_id', '=', period_plannings.ids)])
        if purchase_plannings:
            view = self.env.ref('sale_planning.merge_purchase_planning')
            ctx = {'default_period_id': self.id, 'default_season_id': self.season_id.id,
                   'default_year_id': self.year_id.id}
            return {
                'name': _t('Merge purchase planning'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'merge.purchase.planning.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': ctx,
            }
        self.create_purchase_planning()

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
    def create_purchase_planning(self):
        # Récupération des lignes sale_planning correspondant à season + year
        # Création d'une liste si sale_qty+reserve_qty > 0
        sale_plannings = self.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        # Méthode récursive où on créé une map <materiel, qté>
        dict_product = self._get_dict_product(sale_plannings)
        # Création des purchase_planning associé
        purchase_plannings = self.env['purchase.planning']
        purchase_plannings |= self.env['purchase.planning'].create([{
            'period_id': self.id,
            'product_id': prod.id,
            'supplier_id': prod.seller_ids[:1].id,
            'retained_qty': dict_res,
        } for prod, dict_res in dict_product.items()])
        # Changement de status des sale_planning de la periode
        self.sale_planning_ids.write({'state': 'confirm'})
        self.write({'sale_state': 'confirm'})
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
    def merge_purchase_planning(self, purchase_planning):
        sale_plannings = self.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        purchase_lines = self.env['purchase.planning'].search([('period_id', '=', purchase_planning.id)])
        dict_product = self._get_dict_product(sale_plannings)
        purchase_plannings = self.env['purchase.planning']
        for prod, dict_res in dict_product.items():
            line = purchase_lines.filtered(lambda r: r.product_id == prod)
            if line:
                # on update les quantités
                line.write({'retained_qty': line.retained_qty + dict_res})
            else:
                purchase_plannings |= self.env['purchase.planning'].create({
                    'period_id': purchase_planning.id,
                    'product_id': prod.id,
                    'supplier_id': prod.seller_ids[:1].id,
                    'retained_qty': dict_res,
                })
        self.sale_planning_ids.write({'state': 'confirm'})
        self.write({'sale_state': 'confirm'})
        # Redirection vers les lignes que l'on vient de créer
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Forecast',
            'res_model': 'purchase.planning',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': self.env.context,
            'domain': [('period_id', '=', purchase_planning.id)],
        }

    @api.multi
    def merge_products(self, product_ids):
        return self.env['sale.planning'].create([{
            'period_id': self.id,
            'product_id': product.id,
            'state': 'draft',
            'categ_id': product.categ_id.id,
        } for product in product_ids])

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
        return dict_product

    @api.multi
    def confirm_purchase_planning(self):
        self.ensure_one()
        super(PeriodPlanning, self).confirm_purchase_planning()
        # Récupération des sale_planning associées
        sale_plannings = self.sale_planning_ids.filtered(lambda r: (r.sale_qty + r.reserve_qty > 0))
        season_date = self.season_id.name_get()
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
            }
            self.env['procurement.group'].run(product, planning.sale_qty, product.uom_id, stock_location,
                                              season_date[0][1], season_date[0][1], values)
            planning.write({'state': 'done'})
        # Changement de statut  des sale_planning
        self.sale_planning_ids.write({'state': 'done'})
        self.write({
            'sale_state': 'done',
        })
