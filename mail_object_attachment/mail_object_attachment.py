# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class EmailTemplate(models.Model):
    _inherit = "email.template"

    send_object_attachments = fields.Boolean(u"Attach Object Attachements")

    def generate_email_batch(self, cr, uid, template_id, res_ids, context=None, fields=None):
        res = super(EmailTemplate, self).generate_email_batch(cr, uid, template_id, res_ids, context=context,
                                                              fields=fields)
        return self.generate_email_batch_new_api(cr, uid, template_id, res_ids, fields=fields, res=res, context=context)

    @api.model
    def generate_email_batch_new_api(self, template_id, res_ids, fields=None, res=None):
        res_ids_to_templates = self.get_email_template_batch(template_id, res_ids)
        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        for template, template_res_ids in templates_to_res_ids.iteritems():
            if template.send_object_attachments:
                for res_id in template_res_ids:
                    obj_attachments = self.env['ir.attachment'].search([('res_model', '=', res[res_id].get('model')),
                                                                        ('res_id', '=', res_id)])
                    print "obj_att: %s" % obj_attachments
                    mail_attachments = res[res_id].get('attachment_ids', [])
                    mail_attachments.extend([(4, a.id) for a in obj_attachments])
                    res[res_id].update({
                        'attachment_ids': mail_attachments
                    })
        return res
