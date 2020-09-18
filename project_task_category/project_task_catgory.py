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

from odoo import fields, models, api
from odoo.osv import expression


class ProjectTaskCategory(models.Model):
    _name = 'project.task.category'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _separator = ' / '

    parent_id = fields.Many2one('project.task.category', u"Parent Category", index=True, ondelete='cascade')
    child_ids = fields.One2many('project.task.category', 'parent_id', u"Child Categories")
    parent_left = fields.Integer('# Left Parent', index=1)
    parent_right = fields.Integer('# Right Parent', index=1)

    name = fields.Char(u"Name")
    project_id = fields.Many2one('project.project', string=u"Project")
    active = fields.Boolean(u"Active", default=True)

    @api.model
    def name_create(self, name):
        category_names = name.split(self._separator.strip())
        parents = [category_name.strip() for category_name in category_names]
        child = parents.pop()
        if parents:
            names_id = self.search([
                ('project_id', '=', self.env.context.get('default_project_id')),
                ('name', 'ilike', parents[0])
            ])
            if names_id:
                return super(ProjectTaskCategory, self.with_context(default_parent_id=names_id.id)).name_create(child)
        return super(ProjectTaskCategory, self).name_create(name)

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, self._separator.join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(self._separator.strip())
            parents = [category_name.strip() for category_name in category_names]
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(self._separator.join(parents), args=args, operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('parent_id', 'in', categories.ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator, self._separator.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]), limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    category_id = fields.Many2one('project.task.category', string=u"Categorie")


class ProjectProject(models.Model):
    _inherit = 'project.project'

    category_ids = fields.One2many('project.task.category', 'project_id', string=u"Categories")
