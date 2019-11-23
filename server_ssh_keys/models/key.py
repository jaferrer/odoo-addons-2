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

from paramiko import pkey

from odoo import fields, models, api, exceptions


class SshKeys(models.Model):
    _name = 'ssh.key'
    _description = u"SSH Key"

    name = fields.Char(u"Key Name", required=True, index=True)
    user_id = fields.Many2one('res.users', string=u"User", required=True)
    key = fields.Text(u"Content", help=u"Paste here the ssh public key", required=True)

    @api.constrains('key')
    def check_key_format(self):
        try:
            pkey.PublicBlob.from_string(self.key)
        except (ValueError, TypeError) as e:
            raise exceptions.ValidationError(u"Le format de la clé SSH est invalide: %s" % e)
