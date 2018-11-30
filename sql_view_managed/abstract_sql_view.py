# -*- coding: utf8 -*-

#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import models, exceptions, _, modules
from openerp.tools import drop_view_if_exists


class AbstractSqlView(models.AbstractModel):
    _name = 'sql.view.managed'
    _auto = False

    _current_module = ""
    _sql_file_name = ""
    _query_static_param = ()

    def init(self, cr):
        if self._name != 'sql.view.managed':
            if not self._current_module:
                raise exceptions.except_orm(_(u"Error!"), _(u"Please set the _sql_dir_module with the "
                                                            u"module where the sql dir of your view exist"))
            _sql_file_name = self._sql_file_name or self._table
            drop_view_if_exists(cr, self._table)
            module_path = modules.get_module_path(self._current_module)
            with open('%s/sql/%s.sql' % (module_path, _sql_file_name)) as sql_file:
                sql = "CREATE OR REPLACE VIEW %s AS (%s)" % (self._table, sql_file.read())
                cr.execute(sql, self._query_static_param)
                cr.commit()

