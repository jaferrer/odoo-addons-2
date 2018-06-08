# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, _
from openerp.exceptions import UserError

POSSIBLE_TEMPERATURES = [(str(index), str(index)) for index in range(-30, 31)] + [('no_object', u"No object")]


class FoodReceptionProductCategory(models.Model):
    _inherit = 'product.category'

    maximal_core_temperature = fields.Selection(POSSIBLE_TEMPERATURES, string=u"Maximal core temperature")
    refusal_temperature = fields.Selection(POSSIBLE_TEMPERATURES, string=u"Refusal temperature")
    health_approval = fields.Selection([('yes', u"Yes"), ('no', u"No")], string=u"Health approval")
    dlc_dluo = fields.Selection([('dlc', u"DLC"),
                                 ('dluo', u"DLUO"),
                                 ('dlc_dluo', u"DLC or DLUO"),
                                 ('no', u"No")], string=u"DLC/DLUO")
    packaging_type = fields.Char(string=u"Packaging type")


class FoodReceptionProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_reception_temperatures(self):
        self.ensure_one()
        maximal_core_temperature = refusal_temperature = 'no_object'
        category = self.categ_id
        while category and (maximal_core_temperature == 'no_object' or
                            refusal_temperature == 'no_object') and (category.maximal_core_temperature or
                                                                     category.refusal_temperature):
            if maximal_core_temperature == 'no_object':
                maximal_core_temperature = category.maximal_core_temperature
            if refusal_temperature == 'no_object':
                refusal_temperature = category.refusal_temperature
            category = category.parent_id
        return maximal_core_temperature, refusal_temperature


class FoodReceptionPackop(models.Model):
    _inherit = 'stock.pack.operation'

    maximal_core_temperature = fields.Selection(POSSIBLE_TEMPERATURES,
                                                string=u"Maximal core temperature",
                                                compute='_compute_reception_temperatures')
    refusal_temperature = fields.Selection(POSSIBLE_TEMPERATURES,
                                           string=u"Refusal temperature",
                                           compute='_compute_reception_temperatures')
    reception_temperature = fields.Float(string=u"Reception temperature")

    @api.depends('product_id', 'product_id.categ_id')
    @api.multi
    def _compute_reception_temperatures(self):
        for rec in self:
            maximal_core_temperature = 'no_object'
            refusal_temperature = 'no_object'
            if rec.product_id:
                maximal_core_temperature, refusal_temperature = rec.product_id.get_reception_temperatures()
            rec.maximal_core_temperature = maximal_core_temperature
            rec.refusal_temperature = refusal_temperature


class FoodReceptionStockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def do_new_transfer(self):
        force_fill_temperatures = bool(self.env['ir.config_parameter'].
                                       get_param('l10n_food_reception.force_fill_reception_temperatures', False))
        if not force_fill_temperatures:
            return super(FoodReceptionStockPicking, self).do_new_transfer()
        for rec in self:
            all_packop_null = all([x.qty_done == 0.0 for x in rec.pack_operation_ids])
            for packop in rec.pack_operation_ids:
                if packop.product_id and packop.refusal_temperature != 'no_object' and \
                        (all_packop_null or packop.qty_done):
                    if not packop.reception_temperature:
                        raise UserError(_(u"Please fill reception temperature for product %s") %
                                        packop.product_id.display_name)
                    elif float(packop.reception_temperature) > float(packop.refusal_temperature):
                        raise UserError(_(u"Product %s: you are not allowed to receive goods at this temperature") %
                                        packop.product_id.display_name)
        return super(FoodReceptionStockPicking, self).do_new_transfer()
