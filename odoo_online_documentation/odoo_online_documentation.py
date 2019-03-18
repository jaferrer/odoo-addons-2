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

import base64
import logging
import os
import shutil
import subprocess

_logger = logging.getLogger(__name__)

from openerp import modules, models, fields, api


class OdooOnlineDocumentation(models.Model):
    _name = 'odoo.online.documentation'

    name = fields.Char(string=u"Name", required=True)
    path = fields.Char(string=u"Path", required=True)

    @api.multi
    def remove_attachments(self):
        self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()

    @api.multi
    def create_attachment(self, binary, name):
        self.ensure_one()
        if not binary:
            return False
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'res_model': self._name,
            'res_name': name,
            'datas_fname': name,
            'name': name,
            'datas': binary,
            'res_id': self.id,
        })

    @api.multi
    def open_documentation(self):
        for rec in self:
            split_path = rec.path.split(os.sep)
            module_name = len(split_path) > 1 and split_path[0] or ''
            file_name_total = len(split_path) > 1 and split_path[-1] or ''
            file_name_total_split = file_name_total and file_name_total.split(os.extsep) or ''
            file_name_no_extension = len(file_name_total_split) > 1 and file_name_total_split[0] or ''
            module_path = modules.get_module_path(module_name)
            path_from_module = len(split_path) > 1 and os.sep.join(split_path[1:]) or ''
            total_path = os.sep.join([module_path, path_from_module])
            total_path_split = total_path.split(os.sep)
            total_path_no_filename = len(total_path_split) >= 2 and os.sep.join([item for item in
                                                                                 total_path_split[:-1]]) or ''
            folders_before_generation = [item for item in os.listdir(total_path_no_filename) if
                                         os.path.isdir(os.path.join(total_path_no_filename, item))]
            files_before_generation = [item for item in os.listdir(total_path_no_filename) if
                                       os.path.isfile(os.path.join(total_path_no_filename, item))]
            # We have to run all the process from the same directory).
            # That is why we delete the created files at the end of the process
            _logger.info(u"Generatig doc from path %s" % total_path)
            cmd = subprocess.Popen('asciidoctor-pdf -r asciidoctor-diagram ' + total_path,
                                   stderr=subprocess.STDOUT, shell=True, stdout=subprocess.PIPE)
            cmd.wait()
            _logger.info(u"File generation finished, returned %s" % cmd.returncode)
            with open(total_path_no_filename + os.sep + file_name_no_extension + '.pdf', 'rb') as file:
                content = file.read()
                rec.remove_attachments()
                attachment = rec.create_attachment(base64.encodestring(content), rec.name + '.pdf')
            folders_after_generation = [item for item in os.listdir(total_path_no_filename) if
                                        os.path.isdir(os.path.join(total_path_no_filename, item))]
            files_after_generation = [item for item in os.listdir(total_path_no_filename) if
                                      os.path.isfile(os.path.join(total_path_no_filename, item))]
            created_folders = [item for item in folders_after_generation if item not in folders_before_generation]
            created_files = [item for item in files_after_generation if item not in files_before_generation]
            for created_folder in created_folders:
                total_path_to_created_folder = total_path_no_filename + os.sep + created_folder
                _logger.info(u"Removing folder %s" % total_path_to_created_folder)
                shutil.rmtree(total_path_to_created_folder)
            for created_file in created_files:
                total_path_to_created_file = total_path_no_filename + os.sep + created_file
                _logger.info(u"Removing file %s" % total_path_to_created_file)
                os.remove(total_path_to_created_file)
            url = "/web/binary/saveas?model=ir.attachment&field=datas&id=%s&filename_field=name" % attachment.id
            return {
                "type": "ir.actions.act_url",
                "url": url,
                "target": "self"
            }
