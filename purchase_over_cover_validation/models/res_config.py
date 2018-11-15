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

from openerp import fields, models, api


class purchase_jit_config(models.TransientModel):
    _inherit = 'purchase.config.settings'

    nb_days_max_cover = fields.Integer(string=u"Maximal number days for cover")

    @api.multi
    def get_default_nb_days_max_cover(self):
        nb_days_max_cover = self.env['ir.config_parameter'].get_param(
            "purchase_over_cover_validation.nb_days_max_cover", default=0)
        return {'nb_days_max_cover': int(nb_days_max_cover)}

    @api.multi
    def set_nb_days_max_cover(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_over_cover_validation.nb_days_max_cover",
                                        record.nb_days_max_cover or '0')
