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
from openerp import models, exceptions


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
    if is_module_installed(self.env, 'bus_integration'):
        object_mapping = self.env['bus.object.mapping'].get_mapping(self._name)
        if object_mapping:
            raise exceptions.except_orm(u"Bus Error", u"Impossible to delete record on model %s, use for bus "
                                                      u"synchronisation" % self._name)
    res_unlink = UNLINK_ORIGINAL(self)
    return res_unlink


models.BaseModel.unlink = unlink
