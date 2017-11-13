# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api
from openerp.models import BaseModel


class BaseModelExtend(models.BaseModel):
    _name = 'basemodel.extend'

    def _register_hook(self, cr):
        @api.multi
        def new_export_rows(self, fields):
            """ Export fields of the records in ``self``.

                        :param fields: list of lists of fields to traverse
                        :return: list of lists of corresponding values
                    """
            lines = []
            for record in self:
                # main line of record, initially empty
                current = [''] * len(fields)
                lines.append(current)

                # list of primary fields followed by secondary field(s)
                primary_done = []

                # process column by column
                for i, path in enumerate(fields):
                    if not path:
                        continue

                    name = path[0]
                    if name in primary_done:
                        continue

                    if name == '.id':
                        current[i] = str(record.id)
                    elif name == 'id':
                        current[i] = record.export_xml_id()
                    else:
                        field = record._fields[name]
                        value = record[name]
                        # this part could be simpler, but it has to be done this way
                        # in order to reproduce the former behavior
                        if not isinstance(value, BaseModel):
                            current[i] = field.convert_to_export(value, self.env)
                        else:
                            primary_done.append(name)
                            # This is a special case, its strange behavior is intended!
                            if field.type == 'many2many' and len(path) > 1 and path[1] == 'id':
                                xml_ids = [r.export_xml_id() for r in value]
                                current[i] = ','.join(xml_ids) or False
                                continue

                            # recursively export the fields that follow name
                            fields2 = [(p[1:] if p and p[0] == name else []) for p in fields]
                            lines2 = value.new_export_rows(fields2)
                            if lines2:
                                # merge first line with record's main line
                                for j, val in enumerate(lines2[0]):
                                    if val or isinstance(val, bool) or isinstance(val, int):
                                        current[j] = val
                                # check value of current field
                                if not current[i] and not isinstance(current[i], bool) and \
                                        not isinstance(current[i], int):
                                    # assign xml_ids, and forget about remaining lines
                                    xml_ids = [item[1] for item in value.name_get()]
                                    current[i] = ','.join(xml_ids)
                                else:
                                    # append the other lines at the end
                                    lines += lines2[1:]
                            else:
                                current[i] = False

            return lines

        @api.multi
        def new_export_data(self, fields_to_export, raw_data=False):
            """ Export fields for selected objects

                      :param fields_to_export: list of fields
                      :param raw_data: True to return value in native Python type
                      :rtype: dictionary with a *datas* matrix

                      This method is used when exporting data via client menu
                  """
            fields_to_export = map(models.fix_import_export_id_paths, fields_to_export)
            if raw_data:
                self = self.with_context(export_raw_data=True)
            return {'datas': self.new_export_rows(fields_to_export)}

        def export_xml_id(self):
            """ Return a valid xml_id for the record ``self``. """
            if not self._is_an_ordinary_table():
                raise Exception(
                    "You can not export the column ID of model %s, because the "
                    "table %s is not an ordinary table."
                    % (self._name, self._table))
            ir_model_data = self.sudo().env['ir.model.data']
            data = ir_model_data.search([('model', '=', self._name), ('res_id', '=', self.id)])
            if data:
                if data[0].module:
                    return '%s.%s' % (data[0].module, data[0].name)
                else:
                    return data[0].name
            else:
                postfix = 0
                name = '%s_%s' % (self._table, self.id)
                while ir_model_data.search([('module', '=', '__export__'), ('name', '=', name)]):
                    postfix += 1
                    name = '%s_%s_%s' % (self._table, self.id, postfix)
                ir_model_data.create({
                    'model': self._name,
                    'res_id': self.id,
                    'module': '__export__',
                    'name': name,
                })
                return '__export__.' + name
        BaseModel.export_data = new_export_data
        BaseModel.new_export_rows = new_export_rows
        BaseModel.export_xml_id = export_xml_id
        return super(BaseModelExtend, self)._register_hook(cr)
