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

import openerp
from openerp import models


def is_module_installed(env, module_name):
    """ Check if an Odoo addon is installed.

    :param module_name: name of the addon
    """
    # the registry maintains a set of fully loaded modules so we can
    # lookup for our module there
    return module_name in env.registry._init_modules


UNLINK_ORIGINAL = models.BaseModel.unlink


@openerp.api.multi
def unlink(self):
    ids = self.ids
    res_unlink = UNLINK_ORIGINAL(self)
    if is_module_installed(self.env, 'bus_integration'):
        object_mapping = self.env['object.mapping'].search([('name', '=', self._name)])
        if object_mapping.deactivate_on_delete:
            recs = self.search([('id', 'in', ids)])
            if not recs and res_unlink:
                for id in ids:
                    sync_histo = self.env['bus.model.extend'].search([('model', '=', self._name),
                                                                      ('openerp_id', '=', id)])
                    if sync_histo:
                        sync_histo.write({'to_deactivate': True})
                    else:
                        self.env['bus.model.extend'].create({
                            'model': self._name,
                            'openerp_id': id,
                            'to_deactivate': True
                        })
    return res_unlink


models.BaseModel.unlink = unlink
