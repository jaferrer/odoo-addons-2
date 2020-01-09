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

from odoo import fields, models


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    active = fields.Boolean(u"Actif", default=True)

    for_company_type = fields.Selection([
        ('person', u"Particulier"),
        ('company', u"Société")
    ], u"Type de personne", required=True, default='person')

    _sql_constraints = [
        ('name_uniq', 'unique (name, for_company_type)', u"Ce nom existe deja pour ce type de personne")
    ]
