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
import io

import unicodecsv as csv

from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from odoo import exceptions
from odoo import models, fields, api
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)


class CustomerFileToImport(models.Model):
    _name = 'customer.file.to.import'
    _description = "Customer file to import"
    _order = 'sequence,id'

    name = fields.Char(string=u"Nom", required=True, readonly=True)
    asynchronous = fields.Boolean(string=u"Asynchronous importation", readonly=True)
    chunk_size = fields.Integer(string=u"Chunk size for asynchronous importation")
    file = fields.Binary(string=u"File to import", attachment=True)
    nb_columns = fields.Integer(string=u"Number of columns", readonly=True)
    state = fields.Selection([('draft', u"To import"),
                              ('csv_generated', u"CSV generated"),
                              ('importing', u"Importing"),
                              ('error', u"Error during importation"),
                              ('done', u"Done")], string=u"State", compute='_compute_state')
    log_line_ids = fields.One2many('customer.importation.log.line', 'import_id', string=u"Log lines", readonly=True)
    log_lines_count = fields.Integer(string=u"Number of log lines", compute='_compute_log_lines_count')
    csv_file_ids = fields.One2many('customer.generated.csv.file', 'import_id', string=u"Generated CSV files",
                                   readonly=True)
    sequence = fields.Integer(string=u"Séquence", readonly=True)
    extension = fields.Char(string=u"Extension", readonly=True, help=u"Example : '.xls', '.csv' or '.txt'")
    datas_fname = fields.Char(string=u"Donloaded file name", compute='_compute_datas_fname')

    def _compute_datas_fname(self):
        for rec in self:
            rec.datas_fname = u"%s%s" % (rec.name, rec.extension)

    def _compute_log_lines_count(self):
        for rec in self:
            rec.log_lines_count = len(rec.log_line_ids)

    def _compute_state(self):
        for rec in self:
            state = 'draft'
            if any([file.state == 'importing' for file in rec.csv_file_ids]):
                state = 'importing'
            elif any([file.state == 'error' for file in rec.csv_file_ids]):
                state = 'error'
            elif rec.csv_file_ids and all([file.state == 'done' for file in rec.csv_file_ids]):
                state = 'done'
            elif rec.csv_file_ids:
                state = 'csv_generated'
            rec.state = state

    def generate_out_csv_files(self):
        """Method to overwrite for each model"""
        self.ensure_one()

    def action_generate_out_csv_files(self):
        self.ensure_one()
        self.log_info(u"Generating CSV file for %s" % self.name)
        self.state = 'draft'
        self.log_line_ids.unlink()
        self.csv_file_ids.unlink()
        self.generate_out_csv_files()

    def import_actual_files(self):
        self.csv_file_ids.action_import()

    def log(self, type, msg):
        self._log(msg=msg, type=type)

    def _log(self, msg, type='INFO'):
        self.ensure_one()
        if type == 'INFO':
            _logger.info(msg)
        elif type == 'WARNING':
            _logger.warning(msg)
        elif type == 'ERROR':
            _logger.error(msg)
        else:
            _logger.info(type + " : " + msg)
        self.env['customer.importation.log.line'].create({
            'import_id': self.id,
            'type': type,
            'message': msg,
        })

    def log_info(self, msg):
        self._log(msg)

    def log_warning(self, msg):
        self._log(msg, type='WARNING')

    def log_error(self, msg):
        self._log(msg, type='ERROR')

    @api.model
    def get_external_id_or_create_one(self, object, module=None):
        object.ensure_one()
        xlml_id = object.get_external_id()[object.id]
        if not xlml_id:
            self.env['ir.model.data'].create({
                'module': module or '',
                'name': object._name.replace('.', '_') + '_' + str(object.id),
                'model': object._name,
                'res_id': object.id
            })
            xlml_id = object.get_external_id()[object.id]
        if not xlml_id:
            raise exceptions.UserError(u"Impossible de générer un ID XML pour l'objet %s" % object)
        return xlml_id

    def save_data(self, model, data, fields_to_import=None, sequence=0):
        fields_to_import = fields_to_import or list(list(data.values())[0].keys())
        self.save_generated_csv_file(model, fields_to_import, data, sequence=sequence)

    def save_generated_csv_file(self, model, fields_to_import, table_dict_result, sequence=0):
        self.ensure_one()
        model_obj = self.env['ir.model'].search([('model', '=', model)])
        if len(model_obj) != 1:
            raise exceptions.UserError(u"Model %s not found." % model)
        out_file = io.BytesIO()
        _logger.info("Creating and fill csv odoo from data")
        # with open(file_path, 'wb') as out_file:
        out_file_csv = csv.writer(out_file)
        out_file_csv.writerow(['id'] + fields_to_import)
        cache_field = set()
        for record_id in table_dict_result:
            row = [record_id]
            for field_name in fields_to_import:
                field_name_formated = field_name.replace('/id', '').replace(':id', '')
                if field_name_formated not in cache_field:
                    cache_field.add(field_name_formated)
                    if self.env['ir.model.fields'].search_count([
                        ('model_id', '=', model_obj.id), ('name', '=', field_name_formated)
                    ]) != 1:
                        raise exceptions.UserError(u"Field %s not found in model %s." % (field_name_formated, model))
                row += [table_dict_result[record_id].get(field_name, '')]
            out_file_csv.writerow(row)
        _logger.info("Save csv odoo from data")
        # with open(file_path, 'rb') as tmpfile:
        self.env['customer.generated.csv.file'].create({
            'import_id': self.id,
            'model': model,
            'sequence': sequence,
            'generated_csv_file': base64.encodebytes(out_file.getvalue()),
            'fields_to_import': str(['id'] + fields_to_import)
        })

    def check_line_length(self, iterable):
        self.ensure_one()
        if len(iterable) != self.nb_columns:
            self.log_error(u"Importation file should have %s columns, not %s" % (self.nb_columns, len(iterable)))
            return False
        return True

    def set_to_import(self):
        for rec in self:
            rec.csv_file_ids.unlink()

    def open_log_lines(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx['search_default_warning'] = True
        ctx['search_default_error'] = True
        ctx['search_default_group_by_type'] = True
        return {
            'name': u"Log lines for CSV files generation of %s" % self.display_name,
            'view_mode': 'tree',
            'res_model': 'customer.importation.log.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.log_line_ids.ids)],
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        _logger.info(u"Creating file %s", vals.get('name', ''))
        return super(CustomerFileToImport, self).create(vals)

    def write(self, vals):
        for rec in self:
            _logger.info(u"Editing file %s", vals.get('name', rec.name))
        return super(CustomerFileToImport, self).write(vals)


class CustomerImportationLogLine(models.Model):
    _name = 'customer.importation.log.line'
    _description = "Customer importation log line"
    _order = 'type'

    import_id = fields.Many2one('customer.file.to.import', string=u"File to import", readonly=True, required=True)
    type = fields.Selection([('ERROR', u"ERROR"), ('WARNING', u"WARNING"), ('INFO', u"INFO")],
                            string=u"Type", readonly=True, required=True)
    message = fields.Char(string=u"Message", readonly=True, required=True)


class CustomerGeneratedCsvFile(models.Model):
    _name = 'customer.generated.csv.file'
    _description = "Customer generated CSV file"
    _order = 'sequence, id'

    import_id = fields.Many2one('customer.file.to.import', string=u"File to import", readonly=True, required=True)
    generated_csv_file = fields.Binary(string=u"Generated CSV File", readonly=True, required=True, attachment=True)
    model = fields.Char(string=u"Model", readonly=True, required=True)
    sequence = fields.Integer(string=u"Sequence", readonly=True)
    datas_fname = fields.Char(string=u"Donloaded file name", compute='_compute_datas_fname')
    fields_to_import = fields.Char(string=u"Fields to import", readonly=True)
    state = fields.Selection([('draft', u"To import"),
                              ('importing', u"Importing"),
                              ('error', u"Error during importation"),
                              ('done', u"Done")], string=u"State", compute='_compute_state')
    imported = fields.Boolean(string=u"Imported")
    imported_file_ids = fields.One2many('customer.imported.csv.file', 'original_file_id', string=u"Imported files")

    def _compute_datas_fname(self):
        for rec in self:
            rec.datas_fname = u"%s.csv" % rec.model

    def download_generated_csv_file(self):
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += '/web/content/%s/%s/generated_csv_file/%s?download=True' % (self._name, self.id, self.datas_fname)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': '_new',
        }

    @api.depends('imported_file_ids', 'imported_file_ids.done', 'imported_file_ids.error')
    def _compute_state(self):
        for rec in self:
            last_imported_file = self.env['customer.imported.csv.file']. \
                search([('id', 'in', rec.imported_file_ids.ids)], order='id desc', limit=1)
            state = 'draft'
            if rec.imported:
                state = 'done'
            elif last_imported_file and last_imported_file.error:
                state = 'error'
            elif last_imported_file and last_imported_file.done:
                state = 'done'
            elif last_imported_file:
                state = 'importing'
            rec.state = state

    def name_get(self):
        return [(rec.id, u"%s, model %s" % (rec.model, rec.import_id.name)) for rec in self]

    def action_import(self):
        for rec in self:
            imported = self.env['customer.imported.csv.file'].create({
                'model': rec.model,
                'csv_file': rec.generated_csv_file,
                'asynchronous': rec.import_id.asynchronous,
                'sequence': rec.sequence,
                'fields_to_import': rec.fields_to_import,
                'original_file_id': rec.id,
                'chunk_size': rec.import_id.chunk_size,
            })
            if not rec.import_id.asynchronous:
                if imported.error_msg:
                    raise UserError(imported.error_msg)
                rec.imported = True


class CustomerGeneratedCsvFileSequenced(models.Model):
    _name = 'customer.imported.csv.file'
    _description = "Customer imported CSV file"
    _order = 'id desc'

    model = fields.Char(string=u"Model", readonly=True, required=True)
    csv_file = fields.Binary(string=u"Generated CSV File", readonly=True, required=True, attachment=True)
    asynchronous = fields.Boolean(string=u"Asynchronous importation", readonly=True)
    chunk_size = fields.Integer(string=u"Chunk size for asynchronous importation")
    sequence = fields.Integer(string=u"Sequence", readonly=True)
    datas_fname = fields.Char(string=u"Donloaded file name", compute='_compute_datas_fname')
    fields_to_import = fields.Char(string=u"Fields to import", readonly=True)
    original_file_id = fields.Many2one('customer.generated.csv.file', u"Original generated file", ondelete='cascade')
    error = fields.Boolean(string=u"Error during importation")
    started = fields.Boolean(string=u"Importation started")
    done = fields.Boolean(string=u"Imported")
    error_msg = fields.Text(string=u"Message d'erreur")
    generated_job_ids = fields.One2many('queue.job', 'imported_file_id', string=u"Generated jobs")
    processed = fields.Boolean(string=u"Traité")

    def _compute_datas_fname(self):
        for rec in self:
            rec.datas_fname = u"%s.csv" % rec.model

    def name_get(self):
        return [(rec.id, u"CSV file importation of model %s" % rec.model) for rec in self]

    def get_default_importation_options(self):
        self.ensure_one()
        return {u'datetime_format': u'%Y-%m-%d %H:%M:%S',
                u'date_format': u"%Y-%m-%d",
                u'keep_matches': False,
                u'encoding': u'utf-8',
                u'fields': [],
                u'quoting': u'"',
                u'headers': True,
                u'separator': u',',
                u'float_thousand_separator': u',',
                u'float_decimal_separator': u'.',
                u'advanced': True}

    def get_default_values_for_importation_wizard(self):
        self.ensure_one()
        return {
            'res_model': self.model,
            'file': base64.b64decode(self.csv_file),
            'file_name': self.datas_fname,
            'file_type': 'text/csv',
        }

    @api.model
    def raise_error_if_needed(self, importation_result):
        self.ensure_one()
        if importation_result:
            msg_unknown_error = u"""Unknown error"""
            error_msg = u""""""
            error = False
            for item in importation_result:
                if item.get('type') == 'error':
                    error = True
                    if error_msg:
                        error_msg += u"""\r"""
                    error_msg += u"""%s""" % item.get('message', msg_unknown_error)
            if error:
                if not error_msg:
                    self.error_msg = msg_unknown_error
                else:
                    self.error_msg = error_msg
                self.error = True

    def launch_importation(self):
        for rec in self:
            fields_to_import = safe_eval(rec.fields_to_import)
            rec.started = True
            default_values_for_importation_wizard = rec.get_default_values_for_importation_wizard()
            wizard = self.env['base_import.import'].create(default_values_for_importation_wizard)
            options = rec.get_default_importation_options()
            existing_attachment_ids = []
            if rec.asynchronous:
                options[u'use_queue'] = True
                options[u'chunk_size'] = rec.chunk_size
                existing_attachment_ids = self.env['ir.attachment'].search([('res_model', '=', 'queue.job')]).ids
            importation_result = wizard.do(fields_to_import, fields_to_import, options=options)
            if rec.asynchronous:
                new_attachments = self.env['ir.attachment'].search([('res_model', '=', 'queue.job'),
                                                                    ('id', 'not in', existing_attachment_ids)])
                job_ids = [attachment.res_id for attachment in new_attachments]
                jobs = self.env['queue.job'].search([('id', 'in', job_ids)])
                jobs.write({'imported_file_id': rec.id})
            rec.raise_error_if_needed(importation_result)
            rec.processed = True

    @api.model
    def create(self, vals):
        result = super(CustomerGeneratedCsvFileSequenced, self).create(vals)
        self.process_files_to_import()
        return result

    @api.model
    def process_files_to_import(self):
        if self.env['queue.job'].search([('state', '!=', 'done')]):
            return
        not_processed_files = self.search([('processed', '=', False)])
        if not not_processed_files:
            return
        min_sequence = min([file.sequence for file in not_processed_files])
        files_to_process = self.search([('processed', '=', False), ('sequence', '=', min_sequence)])
        files_to_process.launch_importation()


class CustomerFileImportationIrAttachment(models.Model):
    _inherit = 'ir.attachment'

    res_model = fields.Char(index=True)
    res_field = fields.Char(index=True)
    res_name = fields.Char(index=True)
    datas_fname = fields.Char(index=True)
    res_id = fields.Integer(index=True)
    company_id = fields.Many2one('res.company', index=True)


class BaseImportImport(models.TransientModel):
    _inherit = 'base_import.import'

    @api.model
    @job
    @related_action('_related_action_attachment')
    def _split_file(self, model_name, translated_model_name, attachment, options, file_name="file.csv"):
        existing_job_ids = self.env['queue.job'].search([]).ids
        result = super(BaseImportImport, self)._split_file(model_name, translated_model_name, attachment, options,
                                                           file_name=file_name)
        job_uuid = self.env.context.get('job_uuid')
        if job_uuid:
            original_job = self.env['queue.job'].search([('uuid', '=', job_uuid)])
            if len(original_job) != 1:
                raise exceptions.UserError(u"Impossible to find job for UUID %s" % job_uuid)
            new_jobs = self.env['queue.job'].search([('id', 'not in', existing_job_ids)])
            new_jobs.write({
                'imported_file_id': original_job.imported_file_id and original_job.imported_file_id.id or False,
            })
        return result


class CustomerFileQueueJob(models.Model):
    _inherit = 'queue.job'

    imported_file_id = fields.Many2one('customer.imported.csv.file', string=u"Job généré pour le fichier",
                                       readonly=True)

    def update_importation_file_states(self):
        files_to_update = self.env['customer.imported.csv.file']
        for rec in self:
            files_to_update |= rec.imported_file_id
        for file_to_update in files_to_update:
            files_to_update.error = False
            files_to_update.done = False
            if self.search([('imported_file_id', '=', file_to_update.id), ('state', '=', 'failed')]):
                files_to_update.error = True
            elif not self.search([('imported_file_id', '=', file_to_update.id), ('state', '!=', 'done')]):
                files_to_update.done = True

    @api.model
    def create(self, vals):
        result = super(CustomerFileQueueJob, self).create(vals)
        result.update_importation_file_states()
        return result

    def write(self, vals):
        result = super(CustomerFileQueueJob, self).write(vals)
        if vals.get('state'):
            self.update_importation_file_states()
        return result
