# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api

class stock_location_path(models.Model):
    _inherit = 'stock.location.path'

    group_propagation_option = fields.Selection([('none',"Leave Empty"),('propagate',"Propagate")], default="none",
                                                string="Propagation of Procurement Group")

    @api.model
    def _prepare_push_apply(self, rule, move):
        """Set default values for the resulting move of the application of rule.

        Overridden here to set the procurement group according to the group_propagation_option
        :rtype : dict of values
        :param rule: The push rule that is being applied 
        :param move: The move on which the rule is applied
        """
        res = super(stock_location_path, self)._prepare_push_apply(rule, move)
        if rule.group_propagation_option != 'propagate':
            res.update({'group_id': False})
        return res
