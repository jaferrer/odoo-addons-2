# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api, exceptions, _


class ProjectMilestoneDelivery(models.Model):
    _inherit = 'project.delivery'

    milestone_id = fields.Many2one('project.milestone', u"Milestone")


class ProjectDeliveryMilestone(models.Model):
    _inherit = 'project.milestone'

    delivery_ids = fields.One2many('project.delivery', 'milestone_id', u"Deliveries")

    @api.multi
    def close_milestone(self):
        res = super(ProjectDeliveryMilestone, self).close_milestone()
        for delivery in self.delivery_ids:
            if delivery.todo:
                raise exceptions.UserError(_("You can't close a Milestone linked to Delivery not done"))
        return res
