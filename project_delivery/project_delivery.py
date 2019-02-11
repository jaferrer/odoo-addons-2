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

from odoo import fields, models


class ProjectDelivery(models.Model):
    _name = 'project.delivery'

    name = fields.Char(u"Name")
    project_id = fields.Many2one('project.project', u"Project")
    task_ids = fields.Many2many('project.task', 'delivery_task_rel', string=u"Tasks")
    set_task_stage_id = fields.Many2one('project.task.type', u"Step to set for tasks")
    set_task_tags_ids = fields.Many2many('project.tags', string=u"Labels to add on tasks")
    type_id = fields.Many2one('project.delivery.type', string="Deliver type", required=True)
    effective_date = fields.Date(u"Date of delivery", required=True, default=fields.Date.today())
    done_effective_date = fields.Date(u"Date of delivery", readonly=True)
    assignee_id = fields.Many2one('res.users', u"Assignee", required=True, default=lambda self: self.env.user.id)
    done_by_id = fields.Many2one('res.users', u"Deliver", readonly=True)
    state = fields.Selection([('todo', u"TO DO"), ('done', u"DONE")], default='todo')
    active = fields.Boolean(u"Active", default=True)

    def action_delivery(self):
        for rec in self:
            rec.state = 'done'
            rec.done_by_id = self.env.user.id
            rec.done_effective_date = fields.Date.today()


class ProjectDeliveryType(models.Model):
    _name = 'project.delivery.type'

    name = fields.Char(u"Name")
    project_id = fields.Many2one('project.project', u"Project")


class ProjectDeliveryTask(models.Model):
    _inherit = 'project.task'

    delivery_ids = fields.Many2many('project.delivery', 'delivery_task_rel', string=u"Deliveries")
    project_use_delivery = fields.Boolean(
        u"This project use Delivery",
        related='project_id.use_delivery',
        readonly=True
    )


class ProjectDeliveryProject(models.Model):
    _inherit = 'project.project'

    delivery_ids = fields.Many2many('project.delivery', 'delivery_task_rel', string=u"Deliveries")
    use_delivery = fields.Boolean(u"This project use Delivery")
