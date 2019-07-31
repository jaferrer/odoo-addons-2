# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import unicodecsv as csv
from odoo import exceptions
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CustomerFileToImport(models.Model):
    _name = 'customer.file.to.import'
    _order = 'sequence, id'

    name = fields.Char(string=u"Nom", required=True, readonly=True)
    asynchronous = fields.Boolean(string=u"Asynchronous importation", readonly=True)
    file = fields.Binary(string=u"File to import", required=True, attachment=True)
    nb_columns = fields.Integer(string=u"Number of columns", readonly=True)
    logs = fields.Text(string=u"Logs", readonly=True)
    state = fields.Selection([('draft', u"Never imported"),
                              ('processing', u"Processing"),
                              ('error', u"Error"),
                              ('done', u"Done")], string=u"State", required=True, default='draft')
    csv_file_ids = fields.One2many('customer.generated.csv.file', 'import_id', string=u"Generated CSV files",
                                   readonly=True)
    sequence = fields.Integer(string=u"Séquence", readonly=True)
    extension = fields.Char(string=u"Extension", readonly=True, help=u"Example : '.xls', '.csv' or '.txt'")
    datas_fname = fields.Char(string=u"Donloaded file name", compute='_compute_datas_fname')

    @api.multi
    def _compute_datas_fname(self):
        for rec in self:
            rec.datas_fname = u"%s%s" % (rec.name, rec.extension)

    @api.multi
    def generate_out_csv_files_multi(self):
        for rec in self:
            rec.generate_out_csv_files()

    @api.multi
    def generate_out_csv_files(self):
        """Method to overwrite for each model"""
        self.ensure_one()
        self.log_info(u"Generating CSV file for %s" % self.name)
        self.logs = False
        self.state = 'draft'
        self.csv_file_ids.unlink()

    @api.multi
    def import_actual_files(self):
        for file in self.csv_file_ids:
            wizard = self.env['base_import.import'].create({
                'res_model': file.model,
                'file': file.generated_csv_file.decode('base64'),
                'file_name': file.datas_fname,
                'file_type': 'text/csv',
            })
            options = {u'datetime_format': u'',
                       u'date_format': u'',
                       u'keep_matches': False,
                       u'encoding': u'utf-8',
                       u'fields': [],
                       u'quoting': u'"',
                       u'headers': True,
                       u'separator': u',',
                       u'float_thousand_separator': u',',
                       u'float_decimal_separator': u'.',
                       u'advanced': True}
            if self.asynchronous:
                options[u'use_queue'] = True
            wizard.do(fields=eval(file.fields_to_import), options=options)

    @api.multi
    def generate_csv_files_and_import(self):
        self.button_generate_out_csv_files()
        self.button_import_actual_files()

    @api.multi
    def _log(self, msg, type='INFO'):
        self.ensure_one()
        if type == 'INFO':
            _logger.info(msg)
        elif type == 'WARNING':
            _logger.warning(msg)
        elif type == 'ERROR':
            _logger.error(msg)
        logs = u"""%s""" % self.logs
        if logs:
            logs += u"""\n"""
        logs += u"""%s: %s""" % (type, msg)
        self.logs = logs

    @api.multi
    def log_info(self, msg):
        self._log(msg)

    @api.multi
    def log_warning(self, msg):
        self._log(msg, type='WARNING')

    @api.multi
    def log_error(self, msg):
        self._log(msg, type='ERROR')

    @api.model
    def get_extarnal_id_or_create_one(self, object):
        object.ensure_one()
        xlml_id = object.get_external_id()[object.id]
        if not xlml_id:
            self.env['ir.model.data'].create({'name': object._name.replace('.', '_') + '_' + str(object.id),
                                              'model': object._name,
                                              'res_id': object.id})
            xlml_id = object.get_external_id()[object.id]
        if not xlml_id:
            raise exceptions.UserError(u"Impossible de générer un ID XML pour l'objet %s" % object)
        return xlml_id

    @api.multi
    def save_generated_csv_file(self, model, fields_to_import, areas_dict_result, sequence=0):
        self.ensure_one()
        file_path = os.tempnam() + '.csv'
        _logger.info(u"Importation file opened at path %s", file_path)
        with open(file_path, 'w') as out_file:
            out_file_csv = csv.writer(out_file)
            out_file_csv.writerow(['id'] + fields_to_import)
            for area_id in areas_dict_result:
                out_file_csv.writerow([area_id] + [areas_dict_result[area_id].get(field_name, '') for
                                                   field_name in fields_to_import])
        with open(file_path, 'r') as tmpfile:
            self.env['customer.generated.csv.file'].create({'import_id': self.id,
                                                            'model': model,
                                                            'sequence': sequence,
                                                            'generated_csv_file': base64.b64encode(tmpfile.read()),
                                                            'fields_to_import': str(['id'] + fields_to_import)})

    @api.multi
    def check_line_length(self, iterable):
        self.ensure_one()
        if len(iterable) != self.nb_columns:
            self.log_error(u"Importation file should have %s columns, not %s" % (self.nb_columns, len(iterable)))
            return False
        return True


class CustomerGeneratedCsvFile(models.Model):
    _name = 'customer.generated.csv.file'
    _order = 'sequence, id'

    import_id = fields.Many2one('customer.file.to.import', string=u"File to import", readonly=True, required=True)
    generated_csv_file = fields.Binary(string=u"Generated CSV File", readonly=True, required=True)
    model = fields.Char(string=u"Model", readonly=True, required=True)
    sequence = fields.Integer(string=u"Sequence", readonly=True)
    datas_fname = fields.Char(string=u"Donloaded file name", compute='_compute_datas_fname')
    fields_to_import = fields.Char(string=u"Fields to import", readonly=True)

    @api.multi
    def _compute_datas_fname(self):
        for rec in self:
            rec.datas_fname = u"%s.csv" % rec.model
