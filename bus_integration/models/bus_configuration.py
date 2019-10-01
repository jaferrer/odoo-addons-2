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


from openerp import models, fields


class BusConfiguration(models.Model):
    _name = 'bus.configuration'
    _inherit = 'bus.send.message'

    name = fields.Char(u"Name")
    sender_id = fields.Many2one('bus.base', u"Sender")
    bus_configuration_export_ids = fields.One2many('bus.configuration.export', 'configuration_id', string=u"Fields")
    reception_treatment = fields.Selection([('simple_reception', u"Simple reception")], u"Message Reception Treatment",
                                           required=True)
    code = fields.Selection([('ODOO_SYNCHRONIZATION', u"Odoo synchronization")], u"Code exchange", required=True)
    connexion_state = fields.Char(u"Connexion status")
