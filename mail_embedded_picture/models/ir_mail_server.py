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

import lxml.html as html
import re
from email.mime.image import MIMEImage
from uuid import uuid4
from email import Encoders
from openerp import tools, models, api


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def get_attachment_id_by_src(self, src):
        img_id = False
        matches = re.search(r'(/\web/\image\/)[\d]*', src)
        if matches:
            img_id = matches.group(0).split('/')[-1]
        return img_id

    @api.model
    def embedd_ir_attachment(self, message, body_part):
        # a unicode string is required here
        html_unicode_str = tools.ustr(body_part.get_payload(decode=True))
        root = html.document_fromstring(html_unicode_str)
        matching_buffer = {}
        for child in root.iter():
            # have to replace src by cid of the future attachement
            if child.tag == 'img':
                img_id = self.get_attachment_id_by_src(child.attrib.get('src'))
                if img_id:
                    cid = uuid4()
                    cid_id = ''.join('%s' % cid)
                    matching_buffer[img_id] = cid_id
                    child.attrib['src'] = "cid:%s" % cid_id
        del body_part["Content-Transfer-Encoding"]
        # body has to be re-encoded into the message part using
        # the initial output charset
        body_part.set_payload(html.tostring(
            root, encoding=body_part.get_charset().get_output_charset()))
        Encoders.encode_base64(body_part)
        img_attachments = self.env['ir.attachment'].search([('id', 'in', map(int, matching_buffer.keys()))])
        for img in img_attachments:
            content_id = matching_buffer.get("%s" % img.id)
            # our img.datas is already base64
            part = MIMEImage(img.datas, _encoder=lambda a: a,
                             _subtype=img.datas_fname.split(".")[-1].lower(), )
            part.add_header(
                'Content-Disposition', 'inline', filename=img.datas_fname)
            part.add_header('X-Attachment-Id', content_id)
            part.add_header('Content-ID', '<%s>' % content_id)
            part.add_header("Content-Transfer-Encoding", "base64")
            message.attach(part)
        return

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None, smtp_user=None,
                   smtp_password=None, smtp_encryption=None, smtp_debug=False):
        for part in message.walk():
            if part.get_content_subtype() == 'html':
                self.embedd_ir_attachment(message, body_part=part)
                break
        return super(IrMailServer, self).send_email(message, mail_server_id=mail_server_id, smtp_server=smtp_server,
                                                    smtp_port=smtp_port, smtp_user=smtp_user,
                                                    smtp_password=smtp_password, smtp_encryption=smtp_encryption,
                                                    smtp_debug=smtp_debug)
