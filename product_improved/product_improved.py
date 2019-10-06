# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import re

from openerp import models, api, fields
from openerp.osv import expression
from openerp.osv import fields as old_api_fields
from openerp.tools import float_round


class ProductTemplateJit(models.Model):
    _inherit = 'product.template'

    _columns = {
        'seller_id': old_api_fields.many2one('res.partner', string='Main Supplier', track_visibility='onchange',
                                             help="Main Supplier who has highest priority in Supplier List."),
    }

    @api.multi
    def get_main_supplierinfo(self, force_supplier=None, force_company=None):
        self.ensure_one()
        supplier_infos_domain = [('id', 'in', self.seller_ids.ids)]
        if force_supplier:
            supplier_infos_domain += [('name', '=', force_supplier.id)]
        if force_company:
            supplier_infos_domain += ['|', ('company_id', '=', force_company.id), ('company_id', '=', False)]
        return self.env['product.supplierinfo'].search(supplier_infos_domain, order='sequence, id', limit=1)

    @api.model
    def update_seller_ids(self):
        restrict_to_template_ids = self.env.context.get('restrict_to_template_ids', [])
        if not restrict_to_template_ids:
            restrict_to_template_ids = self.search([]).ids
        self.env.cr.execute("""WITH main_supplier_intermediate_table AS (
    SELECT
        pt.id            AS product_tmpl_id,
        min(ps.sequence) AS sequence
    FROM product_template pt
        LEFT JOIN product_supplierinfo ps ON ps.product_tmpl_id = pt.id AND COALESCE(ps.active, FALSE) IS TRUE
    GROUP BY pt.id),

        main_supplier_s AS (
        SELECT
            ps.product_tmpl_id,
            ps.name,
            ROW_NUMBER()
            OVER (PARTITION BY ps.product_tmpl_id
                ORDER BY ps.id ASC) AS constr
        FROM
            product_supplierinfo ps
            INNER JOIN
            main_supplier_intermediate_table ms
                ON ps.product_tmpl_id = ms.product_tmpl_id AND ps.sequence = ms.sequence
        WHERE COALESCE(ps.active, FALSE) IS TRUE)

SELECT
    pt.id          AS product_tmpl_id,
    res_partner.id AS new_seller_id
FROM product_template pt
    LEFT JOIN main_supplier_s ON main_supplier_s.product_tmpl_id = pt.id
    LEFT JOIN res_partner ON res_partner.id = main_supplier_s.name
    LEFT JOIN res_users ON res_partner.user_id = res_users.id
WHERE (res_partner.id IS NULL OR main_supplier_s.constr = 1) AND
      ((res_partner.id IS NULL AND pt.seller_id IS NOT NULL OR res_partner.id IS NOT NULL AND pt.seller_id IS NULL OR
        res_partner.id != pt.seller_id)) AND pt.ID IN %s""", (tuple(restrict_to_template_ids),))
        for res_tuple in self.env.cr.fetchall():
            product = self.browse(res_tuple[0])
            supplier = self.env['res.partner'].browse(res_tuple[1])
            product.seller_id = supplier
        self.env['product.product'].update_seller_ids()


class ProductLabelProductProduct(models.Model):
    _inherit = 'product.product'

    seller_id = fields.Many2one(related='product_tmpl_id.seller_id', store=True, readonly=True,
                                track_visibility='onchange')

    @api.model
    def update_seller_ids(self):
        return False

    @api.multi
    def get_main_supplierinfo(self, force_supplier=None, force_company=None):
        self.ensure_one()
        return self.product_tmpl_id.get_main_supplierinfo(force_supplier=force_supplier, force_company=force_company)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['product.product']
            if operator in positive_operators:
                products = self.search([('default_code', operator, name)] + args, limit=limit)
                if not products:
                    products = self.search([('ean13', operator, name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search(args + [('default_code', operator, name)], limit=limit)
                if not limit or len(products) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(products)) if limit else False
                    products |= self.search(args + [('name', operator, name),
                                                    ('id', 'not in', products.ids)], limit=limit2)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', '|', ('default_code', operator, name), (
                    'default_code', '=', False), ('name', operator, name)], limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', operator, res.group(2))] + args, limit=limit)
        else:
            products = self.search(args, limit=limit)
        result = products.name_get()
        return result


class ProductUomImproved(models.Model):
    _inherit = 'product.uom'

    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', context=None):
        if from_unit == to_unit:
            res_qty = qty
            if round:
                res_qty = float_round(res_qty, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
            return res_qty
        return super(ProductUomImproved, self). \
            _compute_qty_obj(cr, uid, from_unit, qty, to_unit, round, rounding_method, context)

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        if from_uom_id == to_uom_id:
            return price
        return super(ProductUomImproved, self). \
            _compute_price(cr, uid, from_uom_id, price, to_uom_id)


class ProductSupplierinfoImproved(models.Model):
    _inherit = 'product.supplierinfo'

    name = fields.Many2one(index=True)
    active = fields.Boolean(u"Active", default=True)

    @api.multi
    def update_seller_ids_for_products(self):
        templates = self.env['product.template'].search([('id', 'in', [rec.product_tmpl_id.id for rec in self])])
        if templates:
            self.env['product.template'].with_context(restrict_to_template_ids=templates.ids).update_seller_ids()

    @api.model
    def create(self, vals):
        result = super(ProductSupplierinfoImproved, self).create(vals)
        result.update_seller_ids_for_products()
        return result

    @api.multi
    def write(self, vals):
        result = super(ProductSupplierinfoImproved, self).write(vals)
        self.update_seller_ids_for_products()
        return result


class PricelistImproved(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def find_supplierinfo_for_product(self, product, partner_id):
        seller = False
        for seller_id in product.seller_ids:
            if partner_id and seller_id.name.id == partner_id:
                seller = seller_id
                break
        if not seller and product.seller_ids:
            seller = product.seller_ids[0]
        return seller


    @api.model
    def find_supplierinfos_for_product(self, product, partner_id):
        """ :return: recordset of supplierinfo (fourniture d'achat
        for this supplier """
        sellers = []
        for seller_id in product.seller_ids:
            if partner_id and seller_id.name.id == partner_id:
                sellers.append(seller_id)
        if not sellers and product.seller_ids:
            sellers = [product.seller_ids[0]]
        return sellers

