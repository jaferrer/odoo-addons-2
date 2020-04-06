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
from odoo import models, fields, api


class ChooseDeliveryPackage(models.TransientModel):
    _name = 'choose.delivery.package'

    delivery_carrier_id = fields.Many2one('delivery.carrier', string="Produit transporteur")


class StockPickingTypeEasyPackaging(models.Model):
    _inherit = 'stock.picking.type'

    is_easy_packaging = fields.Boolean("Mise en colis simplifiée")
    is_dest_package_mandatory = fields.Boolean("Colis de destination obligatoire")


class StockPickingEasyPackaging(models.Model):
    _inherit = 'stock.picking'

    need_packaging = fields.Boolean("A besoin d'une mise en colis")
    is_easy_packaging = fields.Boolean("Mise en colis simplifiée", related='picking_type_id.is_easy_packaging')
    is_dest_package_mandatory = fields.Boolean("Colis de destination obligatoire",
                                               related='picking_type_id.is_dest_package_mandatory')
