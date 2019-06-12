# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    number = fields.Char(u"Number")

    project_task_sequence_id = fields.Many2one(
        'ir.sequence',
        string=u"Sequence for the task",
        related='project_id.task_sequence_id',
        readonly=True
    )

    @api.multi
    def generate_number(self):
        for rec in self:
            if not rec.project_task_sequence_id:
                raise UserError(_(u"Your project don't have sequence"))
            vals = self.compute_number(self.project_id.id, self.stage_id.id, self.number, force=True)
            if vals:
                rec.write(vals)

    @api.model
    def create(self, vals):
        stage_id = vals.get('stage_id', self.env.context.get('default_stage_id'))
        project_id = vals.get('project_id', self.env.context.get('default_project_id'))
        actual_number = vals.get('actual_number', self.env.context.get('default_number'))
        vals.update(self.sudo().compute_number(project_id, stage_id, actual_number))
        return super(ProjectTask, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            rec_vals = dict(vals)
            stage_id = vals.get('stage_id', rec.stage_id.id)
            project_id = vals.get('project_id', rec.project_id.id)
            actual_number = vals.get('number', rec.number)
            rec_vals.update(self.sudo().compute_number(project_id, stage_id, actual_number))
            super(ProjectTask, rec).write(rec_vals)
        return True

    @api.model
    def compute_number(self, project_id, stage_id, actual_number, force=False):
        vals = {}
        if not actual_number and project_id and stage_id:
            project = self.env['project.project'].browse(project_id)
            if project.task_sequence_id:
                stage = self.env['project.task.type'].browse(stage_id)
                valid_stage = project.auto_generate_number_id and \
                    project.auto_generate_number_id.sequence <= stage.sequence
                if valid_stage or force:
                    vals['number'] = project.task_sequence_id._next()
        return vals

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        result = dict(super(ProjectTask, self).name_search(name, args, operator, limit))
        if name:
            result.update(dict(self.search([('number', operator, name)] + args, limit=limit).name_get()))
        return result

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            if rec.number:
                result.append((rec.id, u"%s - %s" % (rec.number, rec.name)))
            else:
                result.append((rec.id, u"%s" % rec.name))
        return result

class ProjectProject(models.Model):
    _inherit = 'project.project'

    use_sequence = fields.Boolean(u"Use sequence for task")
    task_sequence_id = fields.Many2one('ir.sequence', u"Sequence")
    auto_generate_number_id = fields.Many2one(
        'project.task.type',
        u"When the number is generated",
        domain="[('project_ids', 'in', [active_id])]")


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def default_get(self, fields_list):
        result = super(IrSequence, self).default_get(fields_list)
        project_id = self.env.context.get('for_project_tasks')
        if project_id:
            project = self.env['project.project'].browse(project_id)
            result.update({
                'name': project.name.strip().upper() + _(u" TASK SEQ"),
                'code': project.name.replace(" ", "").strip().lower() + '_code',
                'prefix': 'T',
                'padding': 2
            })
        return result
