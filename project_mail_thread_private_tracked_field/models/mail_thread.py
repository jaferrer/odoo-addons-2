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

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ProjectTask(models.AbstractModel):
    _inherit = 'project.task'

    # This function is repeaded from module "mail_thread_private_tracked_field", because function _track_subtype on
    # project.task does not always calls super
    @api.multi
    def _track_subtype(self, init_values):
        if 'force_subtype_xmlid' in self.env.context:
            res = self.env.context['force_subtype_xmlid']
        else:
            res = super(ProjectTask, self)._track_subtype(init_values)
        return res
