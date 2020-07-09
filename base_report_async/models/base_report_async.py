# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import mimetypes
import os
import tempfile
import zipfile
import time

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from unidecode import unidecode

from genshi.template.eval import UndefinedError

from odoo.addons.queue_job.job import job
from odoo.addons.http_routing.models.ir_http import slugify

from odoo.tools.mimetypes import guess_mimetype

from odoo import api, fields, models, _, exceptions
from odoo import tools

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    async_report = fields.Boolean(u"Asynchronous generation")

    def _create_temporary_report_attachment(self, base64_file, name, force_mimetype=None):
        if not base64_file:
            return False
        mime_type = force_mimetype or guess_mimetype(base64.b64decode(base64_file))
        extension = mimetypes.guess_extension(mime_type)
        if extension == '.xlb':
            extension = '.xls'
        if extension:
            name += extension
        unaccented_name = unidecode(name)
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'res_name': unaccented_name,
            'datas_fname': unaccented_name,
            'name': unaccented_name,
            'mimetype': mime_type,
            'public': True,
            'datas': base64_file,
            'is_temporary_report_file': True
        })

    @api.model
    def launch_asynchronous_report_generation(self, date_start_for_job_creation=None):
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_model or not active_ids:
            raise exceptions.except_orm("Context must provide model and ids for report generation")

        running_jobs_domain = [('user_id', '=', self.env.user.id),
                               ('asynchronous_job_for_report_id', '=', self.id),
                               ('state', 'not in', ['done', 'failed'])]
        if date_start_for_job_creation:
            running_jobs_domain += [('date_created', '<', date_start_for_job_creation)]
        running_job_for_user_and_report = self.env['queue.job'].search(running_jobs_domain, limit=1)
        if running_job_for_user_and_report:
            return True
        description = u"Asynchronous generation of report %s" % self.name
        records_to_print = self.env[active_model].browse(active_ids)
        job_dict = self\
            .with_delay(description=description)\
            .job_asynchronous_report_generation(records_to_print)
        self.env['queue.job']\
            .search([('uuid', '=', job_dict.uuid)])\
            .write({'asynchronous_job_for_report_id': self.id})
        return False

    @job
    @api.multi
    def job_asynchronous_report_generation(self, records_to_print):
        self.ensure_one()
        # needs module web_report_improved
        if 'type_multi_print' in self._fields and self.type_multi_print == 'zip' and len(records_to_print) > 1:
            attachments_to_zip = self.env['ir.attachment']
            index = 0
            for record_to_print in records_to_print:
                index += 1
                _logger.info(u"Generating report for ID %s (%s/%s)", record_to_print.id, index, len(records_to_print))
                try:
                    new_attachment = self.get_attachment_base64_encoded(record_to_print)
                    attachments_to_zip |= new_attachment
                except (exceptions.ValidationError, exceptions.MissingError, exceptions.except_orm,
                        ValueError, UndefinedError, AttributeError, TypeError) as error:
                    self.send_failure_mail(error)
                    return
            zip_file_name = '%s' % (slugify(self.name.replace('/', '-')) or 'documents')
            temp_dir = tempfile.mkdtemp()
            zip_file_path = '%s/%s' % (temp_dir, zip_file_name)
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for att in attachments_to_zip:
                    b64_data = att.with_context(bin_size=False).datas
                    zip_file.writestr(att.datas_fname.replace(os.sep, '-'), base64.b64decode(b64_data))
            with open(zip_file_path, 'rb') as zf:
                b64_data = base64.b64encode(zf.read())
                attachment = self._create_temporary_report_attachment(b64_data, zip_file_name,
                                                                      force_mimetype='application/zip')
        else:
            try:
                attachment = self.get_attachment_base64_encoded(records_to_print)
            except (exceptions.ValidationError, exceptions.MissingError, exceptions.except_orm,
                    ValueError, UndefinedError, AttributeError, TypeError) as error:
                self.send_failure_mail(error)
                return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + "/web/content/%s/%s?download=true" % (attachment.id, attachment.name)
        self.send_mail_report_async_to_user(url)
        return u"report generated"

    @api.multi
    def get_attachment_base64_encoded(self, record):
        self.ensure_one()
        name = u"Report"
        if self.print_report_name:
            if len(record) == 1:
                name = eval(self.print_report_name, {'object': record, 'time': time})
            else:
                name = self.display_name
        data = {
            'model': record._name,
            'ids': record.ids,
        }
        pdf_data, _ = self.render(record.ids, data)
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
        mail = self.env['mail.mail'].create(self.with_context(lang=self.env.user.lang).
                                            get_mail_data_report_async_success(url))
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
        _logger.error(error)
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
    _description = u"Generation de rapports asynchrones"

    message = fields.Char(string=u"Message", readonly=True)
