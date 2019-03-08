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

from openerp import api, models
from openerp.addons.connector.session import ConnectorSession
from .. import jobs


class BackendBus(models.Model):
    _name = 'backend.bus'

    @api.model
    def recep_message(self, archive):
        self.sudo()
        jobs.recep_message.delay(
            ConnectorSession.from_env(self.env),
            "bus.model.extend",
            0,
            archive)
        return True
