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
import socket

from odoo import fields, models, api, exceptions, _


class AuthorizedIP(models.Model):
    _name = 'authorized.ip'
    _description = u"An IP from which connection is authorized without MFA"

    name = fields.Char(u"Address", required=True)
    company_id = fields.Many2one('res.company', u"Company", required=True, ondelete='cascade',
                                 default=lambda self: self.env.user.company_id)

    @api.constrains('name')
    def _check_valid_ip(self):
        if not self.check_ip_is_valid(self.name):
            raise exceptions.ValidationError(_(u"Supplied IP address is invalid"))

    @api.model
    def check_ip_is_valid(self, ip):
        try:
            socket.inet_pton(socket.AF_INET, ip)
            return True
        except socket.error:
            return False

    @api.model
    def check_ip(self, ip):
        if ip == '127.0.0.1':
            return True
        if not self.check_ip_is_valid(ip):
            raise exceptions.UserError(_(u"Invalid IP: %s" % ip))
        return any(aip.name == ip for aip in self.search([]))

    @api.model
    def ips_defined(self):
        return bool(self.search([]))
