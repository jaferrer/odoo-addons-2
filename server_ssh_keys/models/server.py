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

from odoo import fields, models


class SSHServer(models.Model):
    _name = 'ssh.server'
    _description = u"SSH Server"

    name = fields.Char(u"Server's FQDN", required=True, index=True)
    allowed_user_ids = fields.One2many('ssh.server.user', 'server_id', string=u"Allowed Users")
    note = fields.Text(u"Notes")

    def allowed_keys_contents(self, role_name):
        """Returns a list of allowed keys contents for the given role on this server."""
        self.ensure_one()
        role = self.env['ssh.role'].search([('name', '=', role_name)])
        if not role:
            return []
        roles = self.env['ssh.role'].search(['|', ('id', '=', role.id), ('implied_ids', '=', role.id)])
        allowed_users = self.env['ssh.server.user'].search([('server_id', '=', self.id), ('role_id', 'in', roles.ids)])
        keys = []
        for allowed_user in allowed_users:
            for key in allowed_user.user_id.ssh_key_ids:
                keys.append(key.key)
        return keys


class SSHServerUser(models.Model):
    _name = 'ssh.server.user'
    _description = u"Allowed user of a SSH Server"

    server_id = fields.Many2one('ssh.server', string=u"Server", required=True)
    user_id = fields.Many2one('res.users', string=u"User", required=True)
    role_id = fields.Many2one('ssh.role', string=u"Role")
