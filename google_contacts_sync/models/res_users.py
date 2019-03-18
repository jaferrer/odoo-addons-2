# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class GoogleContactUsers(models.Model):
    _inherit = 'res.users'

    google_contacts_rtoken = fields.Char(string="Refresh Token")
    google_contacts_token = fields.Char(string="User token")
    google_contacts_token_validity = fields.Datetime(string="Token Validity")
    google_contacts_last_sync_date = fields.Datetime(string="Last synchro date")
    contact_synchronization = fields.Boolean(u"Synchronisation Google des contacts")
