# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, exceptions, _


class QuantitiesModificationsSaleOrder(models.Model):
    _inherit = 'sale.order'

    workflow_done = fields.Boolean(string="Done state reached in workflow")

    @api.multi
    def reopen_order(self):
        if any([order.state != 'done' for order in self]):
            raise exceptions.except_orm(_("Error!"), _("Impossible to reopen a not done sale order."))
        self.write({'workflow_done': True,
                    'state': 'progress'})
