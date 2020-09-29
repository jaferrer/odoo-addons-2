# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import json
import datetime
import requests

from odoo.exceptions import UserError
from odoo import models, fields, api, _

URL_BASE_API_STAGING = "https://staging-api.yousign.com"
URL_BASE_API_PRODUCTION = "https://api.yousign.com"


class ApiYousignSignature(models.TransientModel):
    _name = 'api.yousign.signature'
    _description = "API Yousign Signature"

    model_name = fields.Char("Model name")
    model_id = fields.Integer("Model ID")
    firstname = fields.Char("Firstname", required=True)
    lastname = fields.Char("Lastname", required=True)
    email = fields.Char("Email", required=True)
    phone = fields.Char("Phone", required=True)
    document_to_sign = fields.Binary("Document to sign")

    @api.model
    def _get_yousign_base_url(self):
        is_test_env = self.sudo().env['ir.config_parameter'].get_param('yousign_staging')
        return URL_BASE_API_STAGING if is_test_env else URL_BASE_API_PRODUCTION

    @api.model
    def access_yousign(self):
        """
        Access to Yousign API.
        """
        session = requests.Session()
        api_key = self.sudo().env['ir.config_parameter'].get_param('yousign_api_key')
        if api_key:
            authorization = "Bearer " + api_key
        else:
            raise UserError(_("No API key, please check your access to Yousign."))

        session.headers.update({
            'Authorization': authorization,
            'accept': u"application/json;",
        })

        return session

    @api.model
    def send_document_to_yousign(self, binary, name):
        """
        Send a document to be signed to Yousign. It MUST be a pdf.
        """
        session = self.access_yousign()
        if not binary:
            raise UserError(_("No document to send"))

        body = {
            'name': "Document %s" % name,
            'type': "signable",
            'content': binary.decode('ascii'),
            'metadata': {
                'source': "Odoo Reanova"
            }
        }
        url = "%s/files" % self._get_yousign_base_url()
        ans = session.post(url, json=body)
        if ans.status_code != 201:
            raise UserError(_("HTTP Request returned a %d error %s" % (ans.status_code, ans.text)))

        return json.loads(ans.text).get('id')

    @api.model
    def create_procedure(self, file_id, name, firstname, lastname, email, phone):
        """
        Create a signature procedure and initialize webhooks to signal the creation of the procedure and its signature.
        """
        session = self.access_yousign()
        id = file_id.replace("/files/", "")
        url = "%s/files/%s/layout" % (self._get_yousign_base_url(), id)
        file_infos = session.get(url)
        page_number = len(json.loads(file_infos.text).get('pages'))
        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')
        url_procedure_started = base_url + "/yousign/webhook/procedure_started"
        url_procedure_finished = base_url + "/yousign/webhook/member_finished"

        webhook_key = self.sudo().env['ir.config_parameter'].get_param('yousign_webhook')
        body = {
            'name': "Procedure %s" % name,
            'description': "Sweet description of procedure",
            'config': {
                'email': {
                    'procedure.started': [
                        {
                            'to': ["@members.auto"],
                            'subject': "Signez votre document avec Yousign",
                            'message': "Bonjour, {{ components.spacer() }} vous êtes invités via Yousign à signer votre"
                                       " document de façon certifiée. Pour cela, veuillez cliquer sur le bouton "
                                       "ci-dessous : {{ components.button('Accéder aux documents', url) }} "
                                       "Cordialement, {{ components.spacer() }} Reanova",
                            'fromName': "Reanova"
                        }
                    ]
                },
                'webhook': {
                    'procedure.started': [
                        {
                            'url': url_procedure_started,
                            'method': "POST",
                            'headers': {
                                'X-API-Key': webhook_key
                            }
                        }
                    ],
                    'member.finished': [
                        {
                            'url': url_procedure_finished,
                            'method': "POST",
                            'headers': {
                                'X-API-Key': webhook_key
                            }
                        }
                    ]
                }
            },
            'members': [
                {
                    'firstname': firstname,
                    'lastname': lastname,
                    'email': email,
                    'phone': phone,
                    'fileObjects': [
                        {
                            'file': file_id,
                            'mention': "Lu et approuvé",
                            'page': page_number,
                            'position': "350,50,550,150",
                        }
                    ]
                }
            ],
            'start': True,
            'status': "active"
        }

        url = "%s/procedures" % self._get_yousign_base_url()
        ans = session.post(url, json=body)
        if ans.status_code != 201:
            raise UserError(_("HTTP Request returned a %d error : %s" % (ans.status_code, ans.text)))

        return json.loads(ans.text).get('id')

    @api.model
    def get_signed_document(self, file_id):
        session = self.access_yousign()
        url = "%s/files/%s/download" % (self._get_yousign_base_url(), file_id)
        response = session.get(url)
        return response.content

    @api.multi
    def button_send_signature_mail(self):
        """
        Send the document to sign to Yousign, create a new procedure and send a email for the client to sign.
        """
        self.ensure_one()
        model_record = self.env[self.model_name].browse(self.model_id)
        b64_pdf_file = model_record.sudo().get_document_to_sign()

        # Procédure de signature certifiée à cocher dès le bouton "Valider" cliqué
        # save the date when document is sent
        model_record.write({
            'is_yousign_procedure_on': True,
            'date_send_to_sign': datetime.datetime.now()
        })

        model_record.yousign_doc_id = self.env['api.yousign.signature'].send_document_to_yousign(
            b64_pdf_file,
            model_record.display_name
        )
        model_record.yousign_procedure_id = self.env['api.yousign.signature'].create_procedure(
            model_record.yousign_doc_id,
            model_record.display_name,
            self.firstname,
            self.lastname,
            self.email,
            self.phone,
        )

        validation_message = "Un mail vous à été envoyé à l'adresse %s pour vous permettre de valider la signature." % \
                             self.email
        return {
            'name': 'Procédure de signature certifiée créée!',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'api.yousign.message',
            'target': 'new',
            'context': {'default_validation_message': validation_message},
        }


class ApiYousignMessage(models.TransientModel):
    _name = 'api.yousign.message'
    _description = "API Yousign Message"

    validation_message = fields.Char("Validation message", readonly=1)
