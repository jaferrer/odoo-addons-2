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

from openerp import models, fields, api, exceptions, _


class OdooOnlineDocumentation(models.Model):
    _name = 'odoo.online.documentation'

    name = fields.Char(string=u"Name", required=True)
    path = fields.Char(string=u"Path")
    file = fields.Binary(string=u"File", attachment=True)
    doc_type_id = fields.Many2one('odoo.online.document.type', string=u"Document type")
    nature = fields.Selection([('PJ', _(u"Attached document"))], string=u"Nature", default='PJ', readonly=True)
    seen_in_sales = fields.Boolean(string=u"Must be seen in sales", default=False)
    seen_in_purchases = fields.Boolean(string=u"Must be seen in purchases", default=False)
    seen_in_prod = fields.Boolean(string=u"Must be seen in manufacturing", default=False)
    # product_product_id = fields.Many2one('product.product')

    _sql_constraints = [('path_unique_per_file', 'unique(path)',
                         _(u"You cannot have twice the same file."))]

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
        """
        Function to open an attached document, can call other functions depending on the 'nature' of the document.
        """

        for rec in self:
            # L'ouverture de base se fait à partir d'un fichier en pièce jointe
            if rec.nature == u"PJ":
                rec.remove_attachments()
                attachment = rec.create_attachment(rec.file, rec.name)
                if not attachment:
                    raise exceptions.except_orm(_(u"Error!"), _(u"No file related to this documentation"))
                url = "/web/binary/saveas?model=ir.attachment&field=datas&id=%s&filename_field=name" % attachment.id
                return {
                    "type": "ir.actions.act_url",
                    "url": url,
                    "target": "self"
                }


class OdooOnlineDocumentType(models.Model):
    _name = 'odoo.online.document.type'

    name = fields.Char(string=u"Document type")
