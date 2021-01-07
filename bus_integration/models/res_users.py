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

from openerp import models, api

SUPERUSER_ID = 1


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def is_bus_user(self):
        """ bus data = referential data created in the mother db that cannot be updated in children's db.
        only the administrator and the bus user are allowed to do it. """

        self.ensure_one()
        return self.id in [SUPERUSER_ID, self.env.ref('bus_integration.bus_user').id]
