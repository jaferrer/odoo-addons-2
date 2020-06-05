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

import requests

from odoo.exceptions import UserError
from odoo import models, fields, api, _


class ApiYousignSignature(models.TransientModel):
    _name = 'api.yousign.signature'
    _description = "API Yousign Signature"

    name = fields.Char("Nom pour Yousign")
    firstname = fields.Char("Firstname", required=True)
    lastname = fields.Char("Lastname", required=True)
    email = fields.Char("Email", required=True)
    phone = fields.Char("Phone", required=True)
    yousign_doc_id = fields.Char("ID document Yousign")
    yousign_procedure_id = fields.Char("ID procédure Yousign")
    document_to_sign = fields.Binary("Document à signer")

    @api.model
    def access_yousign(self):
        """
        Access to Yousign API.
        """
        session = requests.Session()
        api_key = "fb8917fa5957ee4d3f5cdaa74f29da9b"
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

        ans = session.post("https://staging-api.yousign.com/files", json=body)
        if ans.status_code != 201:
            raise UserError(_("HTTP Request returned a %d error %s" % (ans.status_code, ans.text)))

        return json.loads(ans.text).get('id')

    @api.model
    def create_procedure(self, file_id, name, firstname, lastname, email, phone):
        """
        Create a signature procedure.
        """
        session = self.access_yousign()
        id = file_id.replace("/files/", "")
        file_infos = session.get("https://staging-api.yousign.com/files/%s/layout" % id)
        page_number = len(json.loads(file_infos.text).get('pages'))
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
                            'url': "https://visum.serveo.net/yousign/webhook/procedure_started",
                            'method': "POST",
                            'headers': {
                                'X-API-key': "Yousign Webhook - Test value"
                            }
                        }
                    ],
                    'member.finished': [
                        {
                            'url': "https://visum.serveo.net/yousign/webhook/procedure_started",
                            'method': "POST",
                            'headers': {
                                'X-API-key': "Yousign Webhook - Test value"
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

        ans = session.post("https://staging-api.yousign.com/procedures", json=body)
        if ans.status_code != 201:
            raise UserError(_("HTTP Request returned a %d error : %s" % (ans.status_code, ans.text)))

        return json.loads(ans.text).get('id')

    @api.multi
    def button_send_signature_mail(self):
        """
        2 options :
        - No yousign_procedure_id : send the document to sign, create a new procedure and send a email for the client to
        sign the document.
        - existing yousign_procedure_id : send a new email for the client to sign the document.
        """
        self.ensure_one()
        self.yousign_doc_id = self.env['api.yousign.signature'].send_document_to_yousign(
            self.document_to_sign,
            self.name
        )
        self.yousign_procedure_id = self.env['api.yousign.signature'].create_procedure(
            self.yousign_doc_id,
            self.name,
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

    validation_message = fields.Char("Message de validation", readonly=1)
