# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class BusBase(models.Model):
    _name = 'bus.base'
    _inherit = 'bus.synchronized.model'

    name = fields.Char(u"Name")
    bus_username = fields.Char(u"BUS user name", required=True)
    active = fields.Boolean(u"Active", default=True)
    url = fields.Char(string=u"Url")

    _sql_constraints = [('uq_constraint_bus_mapping', 'UNIQUE(bus_username)',
                         _(u'bus synchronisation requires unique values for : %s') % 'bus_username')]

    @api.multi
    def name_get(self):
        return [(rec.id, rec.bus_username.replace("base_", "") .upper() or "") for rec in self]

    @api.model
    def create(self, vals):
        res = super(BusBase, self).create(vals)

        # Lorsque l'on crée une nouvelle base, on souhaite que; pour tous les modèles dont on peut choisir les BDD
        # d'export (domain_bus_base_ids notamment dans les partner, partnerinfo, supplierinfo) et qui s'exportent vers
        # toutes les bases existantes sauf elle-même; la nouvelle base s'ajoute automatiquement.
        models = self.env['bus.object.mapping'].search(
            [('can_select_export_to', '=', True)]).mapped('model_id').mapped('model')
        bus_bases = self.env['bus.base']
        # cas de l'export MASTER -> FILLE
        bus_bases = self.env['bus.base'].search([
            ('bus_username', 'not in', ['base_bus', 'base_master', res.bus_username]), ])
        for model in models:
            for record in self.env[model].search([]):
                if record.domain_bus_base_ids == bus_bases:
                    record.domain_bus_base_ids |= res
        return res
