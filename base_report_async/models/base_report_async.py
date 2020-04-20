# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import mimetypes
import os
import tempfile
import time
import zipfile
from datetime import datetime as dt

import unidecode
from dateutil.relativedelta import relativedelta
from odoo.addons.queue_job.job import job
from odoo.addons.http_routing.models.ir_http import slugify

from odoo.tools.mimetypes import guess_mimetype

from odoo import api, fields, models, _, exceptions
from odoo import tools

_logger = logging.getLogger(__name__)


class DelayReport(models.Model):
    _inherit = 'ir.actions.report'

    async_report = fields.Boolean(u"Asynchronous generation")

    def _create_temporary_report_attachment(self, binary, name):
        if not binary:
            return False
        mimetype = guess_mimetype(binary.decode('base64'))
        extension = mimetypes.guess_extension(mimetype)
        if extension == '.xlb':
            extension = '.xls'
        if extension:
            name += extension
        unaccented_name = unidecode.unidecode(name)
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'res_name': unaccented_name,
            'datas_fname': unaccented_name,
            'name': unaccented_name,
            'mimetype': mimetype,
            'public': True,
            'datas': binary,
            'is_temporary_report_file': True
        })

    @api.multi
    def launch_asynchronous_report_generation(self, values, date_start_for_job_creation=None):
        self.ensure_one()
        running_jobs_domain = [('user_id', '=', self.env.user.id),
                               ('asynchronous_job_for_report_id', '=', self.id),
                               ('state', 'not in', ['done', 'failed'])]
        if date_start_for_job_creation:
            running_jobs_domain += [('date_created', '<', date_start_for_job_creation)]
        running_job_for_user_and_report = self.env['queue.job'].search(running_jobs_domain, limit=1)
        if running_job_for_user_and_report:
            return True
        description = u"Asynchronous generation of report %s" % self.name
        job_uuid = self.with_context(description=description).job_asynchronous_report_generation(values)
        new_job = self.env['queue.job'].search([('uuid', '=', job_uuid)])
        new_job.write({'asynchronous_job_for_report_id': self.id})
        return False

    @job
    def job_asynchronous_report_generation(self, values):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')
        if values.get('type_multi_print') == 'zip' and len(active_ids) > 1:
            attachments_to_zip = self.env['ir.attachment']
            nb_records = len(active_ids)
            index = 0
            for active_id in active_ids:
                index += 1
                _logger.info(u"Generating report for ID %s (%s/%s)", active_id, index, nb_records)
                try:
                    new_attachment = self.get_attachment_base64_encoded(active_model, active_id)
                    attachments_to_zip |= new_attachment
                except (exceptions.ValidationError, exceptions.MissingError, exceptions.except_orm) as error:
                    self.send_failure_mail(error)
                    return
            zip_file_name = '%s' % (slugify(values.get('name').replace('/', '-')) or 'documents')
            temp_dir = tempfile.mkdtemp()
            zip_file_path = '%s/%s' % (temp_dir, zip_file_name)
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for att in attachments_to_zip:
                    zip_file.writestr(att.datas_fname.replace(os.sep, '-'),
                                      base64.b64decode(att.with_context(bin_size=False).datas))
            with open(zip_file_path, 'r') as zf:
                attachment = self._create_temporary_report_attachment(base64.b64encode(zf.read()), zip_file_name)
        else:
            try:
                attachment = self.get_attachment_base64_encoded(active_model, active_ids[0])
            except (exceptions.ValidationError, exceptions.MissingError, exceptions.except_orm) as error:
                self.send_failure_mail(error)
                return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + "/web/content/%s/%s" % (attachment.id, attachment.name)
        self.send_mail_report_async_to_user(url)
        return u"report generated"

    @api.multi
    def get_attachment_base64_encoded(self, model, record_id):
        self.ensure_one()
        name = u"Report"
        if self.print_report_name:
            name = eval(self.print_report_name, {'object': self.env[model].browse(record_id), 'time': time})
        data = {
            'model': model,
            'ids': [record_id],
        }
        pdf_data = self.render_qweb_pdf([record_id], data)
        return self._create_temporary_report_attachment(base64.b64encode(pdf_data), name)

    @api.multi
    def get_mail_data_report_async_success(self, url):
        time_to_live = self.env['ir.config_parameter'].sudo().get_param('attachment.report.ttl', 7)
        expiration_date = fields.Date.to_string(dt.today() + relativedelta(days=+int(time_to_live)))
        odoo_bot = self.sudo().env.ref('base.partner_root')
        email_from = odoo_bot.email
        return {
            'email_from': email_from,
            'reply_to': email_from,
            'recipient_ids': [(6, 0, self.env.user.partner_id.ids)],
            'subject': _("Report {} {}").format(self.name, fields.Date.today()),
            'body_html': _("""<p>Your report is available <a href="{}">here</a>.</p>
<p>It will be automatically deleted the {}.</p>
<p>&nbsp;</p>
<p><span style="color: #808080;">
This is an automated message please do not reply.</span></p>""").format(url, expiration_date),
            'auto_delete': False,
        }

    @api.multi
    def send_mail_report_async_to_user(self, url):
        self.ensure_one()
        mail = self.env['mail.mail'].create(self.get_mail_data_report_async_success(url))
        mail.send()

    @api.multi
    def get_mail_data_report_async_fail(self, error):
        odoo_bot = self.sudo().env.ref('base.partner_root')
        email_from = odoo_bot.email
        return {
            'email_from': email_from,
            'reply_to': email_from,
            'recipient_ids': [(6, 0, self.env.user.partner_id.ids)],
            'subject': _("Error while generating report {}").format(self.name),
            'body_html': _("""<p>The generation of your report failed. Here is the error : {}</p>
<p>&nbsp;</p>
<p><span style="color: #808080;">
This is an automated message please do not reply.</span></p>""").format(tools.ustr(error)),
            'auto_delete': False,
        }

    @api.multi
    def send_failure_mail(self, error):
        self.ensure_one()
        mail = self.env['mail.mail'].create(self.get_mail_data_report_async_fail(error))
        mail.send()

    @api.multi
    def notify_user_for_asynchronous_generation(self, running_job_for_user_and_report):
        self.ensure_one()
        message = _(u"Report %s has been generated asynchronously, "
                    u"you will receive the result by email soon.") % self.name
        if running_job_for_user_and_report:
            message = _(u"A job is running for report %s, please wait for the result first.") % self.name
        ctx = dict(self.env.context)
        ctx['default_message'] = message
        return {
            'name': _(u"Asynchronous report generation"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'report.asynchronous.generation.message',
            'target': 'new',
            'context': ctx,
            'domain': []
        }


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_temporary_report_file = fields.Boolean(string=u"Is a temporary report file")

    @api.model
    def cron_delete_temporary_report_files(self):
        time_to_live = self.env['ir.config_parameter'].sudo().get_param('attachment.report.ttl', 7)
        date_to_delete = fields.Date.to_string(dt.today() + relativedelta(days=-int(time_to_live)))
        self.search([('create_date', '<=', date_to_delete),
                     ('is_temporary_report_file', '=', True)]).unlink()


class QueueJob(models.Model):
    _inherit = 'queue.job'

    asynchronous_job_for_report_id = fields.Many2one('ir.actions.report', string=u"Job to generate report")


class ReportAsynchronousGenerationMessage(models.TransientModel):
    _name = 'report.asynchronous.generation.message'
    _description = u"Génération de rapports asynchrones"

    message = fields.Char(string=u"Message", readonly=True)
