# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api
from odoo.osv import expression


class AbstractParentName(models.AbstractModel):
    _name = 'abstract.parent.name'
    _description = 'abstract.parent.name'
    _parent_separation = '/'

    def name_get(self):
        def get_names(rec):
            """ Return the list [rec.name, rec.parent_id.name, ...] """
            res = []
            while rec:
                res.append(rec.name)
                rec = rec[self._parent_name]
            return res

        separator = " %s " % (self._parent_separation)
        return [(rec.id, separator.join(reversed(get_names(rec)))) for rec in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            names = name.split(self._parent_separation)
            records = [n.strip() for n in names]
            parents = list(records)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(self._parent_separation.join(parents), args=args,
                                             operator='ilike', limit=limit)
                result_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    result_ids = self.search([('id', 'not in', result_ids)])
                    domain = expression.OR([[('parent_id', 'in', result_ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', result_ids)], domain])
                for i in range(1, len(records)):
                    domain = [[('name', operator, self._parent_separation.join(records[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            ids = self.search(expression.AND([domain, args]), limit=limit)
        else:
            ids = self.search(args, limit=limit)
        return ids.name_get()
