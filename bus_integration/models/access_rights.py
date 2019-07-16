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

from openerp import models
from openerp import tools

# Skip right verification for the bus user
SUPERUSER_ID = 1


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @tools.ormcache_context(accepted_keys=('lang',))
    def check(self, cr, uid, model, mode='read', raise_exception=True, context=None):
        if uid == SUPERUSER_ID:
            # User root have all accesses
            return True

        bus_user = self.pool.get('ir.model.data').xmlid_to_object(cr, SUPERUSER_ID, 'bus_integration.bus_user', False,
                                                                  context)
        if bus_user and uid == bus_user.id:
            return True
        return super(IrModelAccess, self).check(cr, uid, model, mode, raise_exception, context)


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        bus_user = self.pool.get('ir.model.data').xmlid_to_object(cr, SUPERUSER_ID, 'bus_integration.bus_user', False,
                                                                  context)
        if bus_user and uid == bus_user.id:
            return super(IrRule, self).domain_get(cr, SUPERUSER_ID, model_name, mode, context)
        return super(IrRule, self).domain_get(cr, uid, model_name, mode, context)
