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
# import base64
import logging

from odoo import models, api
# from odoo.exceptions import UserError
# from odoo.tools import pycompat

_logger = logging.getLogger(__name__)

DEFAULT_FIELDS = ['subject',
                  'body_html',
                  'email_from',
                  'email_to',
                  'partner_to',
                  'email_cc',
                  'reply_to',
                  'scheduled_date']


# class MailTemplate(models.Model):
#     "Templates for sending email"
#     _inherit = "mail.template"
#
#     @api.multi
#     def generate_email(self, res_ids, fields=None):
#         """
#         Complete override to allow template with aeroo see line 100
#         Generates an email from the template for given the given model based on
#         records given by res_ids.
#
#         :param template_id: id of the template to render.
#         :param res_id: id of the record to use for rendering the template (model
#                        is taken from template definition)
#         :returns: a dict containing all relevant fields for creating a new
#                   mail.mail entry, with one extra key ``attachments``, in the
#                   format [(report_name, data)] where data is base64 encoded.
#         """
#         self.ensure_one()
#         multi_mode = True
#         if isinstance(res_ids, pycompat.integer_types):
#             res_ids = [res_ids]
#             multi_mode = False
#         if fields is None:
#             fields = list(DEFAULT_FIELDS)
#
#         res_ids_to_templates = self.get_email_template(res_ids)
#
#         # templates: res_id -> template; template -> res_ids
#         templates_to_res_ids = {}
#         for res_id, template in res_ids_to_templates.items():
#             templates_to_res_ids.setdefault(template, []).append(res_id)
#
#         results = dict()
#         for template, template_res_ids in templates_to_res_ids.items():
#             template_ctx = self.env['mail.template']
#             # generate fields value for all res_ids linked to the current template
#             if template.lang:
#                 template_ctx = template_ctx.with_context(lang=template._context.get('lang'))
#             for field in fields:
#                 template_ctx = template_ctx.with_context(safe=field in {'subject'})
#                 generated_field_values = template_ctx.render_template(
#                     getattr(template, field), template.model, template_res_ids,
#                     post_process=(field == 'body_html'))
#                 for res_id, field_value in generated_field_values.items():
#                     results.setdefault(res_id, dict())[field] = field_value
#             # compute recipients
#             if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
#                 results = template.generate_recipients(results, template_res_ids)
#             # update values for all res_ids
#             for res_id in template_res_ids:
#                 values = results[res_id]
#                 # body: add user signature, sanitize
#                 if 'body_html' in fields and template.user_signature:
#                     signature = self.env.user.signature
#                     if signature:
#                         values['body_html'] = tools.append_content_to_html(
#                             values['body_html'],
#                             signature,
#                             plaintext=False
#                         )
#                 if values.get('body_html'):
#                     values['body'] = tools.html_sanitize(values['body_html'])
#                 # technical settings
#                 values.update(
#                     mail_server_id=template.mail_server_id.id or False,
#                     auto_delete=template.auto_delete,
#                     model=template.model,
#                     res_id=res_id or False,
#                     attachment_ids=[attach.id for attach in template.attachment_ids],
#                 )
#
#             # Add report in attachments: generate once for all template_res_ids
#             if template.report_template:
#                 for res_id in template_res_ids:
#                     attachments = []
#                     report_name = self.render_template(template.report_name, template.model, res_id)
#                     report = template.report_template
#                     report_service = report.report_name
#
#                     if report.report_type in ['qweb-html', 'qweb-pdf']:
#                         result, format = report.render_qweb_pdf([res_id])
#                     elif report.report_type == 'aeroo':
#                         result, format, __ = report.render_aeroo([res_id], {})
#                     else:
#                         raise UserError(_('Unsupported report type %s found.') % report.report_type)
#
#                     # TODO in trunk, change return format to binary to match message_post expected format
#                     result = base64.b64encode(result)
#                     if not report_name:
#                         report_name = 'report.' + report_service
#                     ext = "." + format
#                     if not report_name.endswith(ext):
#                         report_name += ext
#                     attachments.append((report_name, result))
#                     results[res_id]['attachments'] = attachments
#
#         return multi_mode and results or results[res_ids[0]]


class Parser(models.AbstractModel):
    _inherit = 'report.report_aeroo.abstract'

    def display_address(self, address_record, without_company=False):
        return address_record._display_address(without_company)

    @api.multi
    def complex_report(self, docids, data, report, ctx):
        ctx = dict(ctx) or {}
        ctx.update({
            'display_address': self.display_address,
        })
        return super(Parser, self).complex_report(docids, data, report, ctx)


class AerooIrModelImproved(models.Model):
    _name = 'ir.model'
    _inherit = 'ir.model'

    def _add_manual_models(self):
        """
        Calls original function + loads Aeroo Reports 'location' reports
        """
        super(AerooIrModelImproved, self)._add_manual_models()
        if 'report_aeroo' in self.pool._init_modules:
            _logger.info('Adding aeroo reports location models')
            self.env.cr.execute("""SELECT report_name, name, parser_loc, id
                    FROM ir_act_report_xml WHERE
                    report_type = 'aeroo'
                    AND parser_state = 'loc'
                    ORDER BY id
                    """)
            for report in self.env.cr.dictfetchall():
                parser = self.env['ir.actions.report'].load_from_file(report['parser_loc'], report['id'])
                parser._build_model(self.pool, self.env.cr)
