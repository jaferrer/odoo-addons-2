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

from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    partner_contact_id = fields.Many2one('res.partner', "Données de contact")
    contact_name = fields.Char(related='partner_contact_id.name')
    contact_email = fields.Char(related='partner_contact_id.email')
    contact_website = fields.Char(related='partner_contact_id.website')
    contact_phone = fields.Char(related='partner_contact_id.phone')
    contact_vat = fields.Char(related='partner_contact_id.vat')
    contact_address = fields.Char(related='partner_contact_id.contact_address')
