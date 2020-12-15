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
from odoo import models, fields, api
from odoo.addons.component.core import Component


class MagentoIrAttachmentAdapter(Component):
    _inherit = 'magento.adapter'
    _name = 'magento.ir.attachment.adapter'
    _apply_on = 'magento.ir.attachment'

    _magento2_key = 'id'

    def _call(self, url, data=None, http_method=None, **kwargs):
        kwargs['storeview'] = 'all'
        return super(MagentoIrAttachmentAdapter, self)._call(url, data, http_method=http_method, **kwargs)

    @staticmethod
    def _normalize_data(record):
        return {'entry': record}

    def create(self, data, comodel_name, comodel_id):
        if self.collection.version == '1.7':
            return super(MagentoIrAttachmentAdapter, self).create(data)
        url = '%s/%s/media' % (comodel_name, comodel_id)
        ans = self._call(url, self._normalize_data(data), http_method='POST')
        return ans

    def write(self, external_id, data, comodel_name, comodel_id):
        if self.collection.version == '1.7':
            return super(MagentoIrAttachmentAdapter, self).write(external_id, data)
        url = '%s/%s/media/%s' % (comodel_name, comodel_id, external_id)
        ans = self._call(url, self._normalize_data(data), http_method='PUT')
        return ans

    def delete(self, external_id, comodel_name, comodel_id):
        if self.collection.version == '1.7':
            return super(MagentoIrAttachmentAdapter, self).delete(external_id)
        url = '%s/%s/media/%s' % (comodel_name, comodel_id, external_id)
        return self._call(url, None, http_method='DELETE')

    def read(self, external_id, comodel_name, comodel_id, **kwargs):
        if self.collection.version == '1.7':
            return super(MagentoIrAttachmentAdapter, self).read(external_id, **kwargs)
        url = '%s/%s/media/%s' % (comodel_name, comodel_id, external_id)
        ans = self._call(url, None, http_method='GET')
        return ans


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    magento_bind_ids = fields.One2many('magento.ir.attachment', 'odoo_id', u"Magento Bindings")

    sequence = fields.Integer(u"Position")


class MagentoIrAttachmentBinder(Component):
    _name = 'magento.ir.attachment.binder'
    _inherit = 'magento.binder'
    _apply_on = ['magento.ir.attachment']


class MagentoIrAttachment(models.Model):
    _name = 'magento.ir.attachment'
    _inherit = 'magento.binding'
    _inherits = {'ir.attachment': 'odoo_id'}
    _description = 'Magento Image'

    odoo_id = fields.Many2one('ir.attachment', u"Image associée", required=True, ondelete='restrict')
    image_type = fields.Selection([
        ('image', u"Image"),
        ('small_image', u"Image réduite"),
        ('thumbnail', u"Aperçu")
    ], compute='_compute_image_type', store=True)
    comodel_external_name = fields.Char()
    comodel_external_id = fields.Char()

    @api.multi
    @api.depends('name')
    def _compute_image_type(self):
        for rec in self:
            if not rec.res_model == 'product.template':
                continue
            if rec.name == 'image':
                rec.image_type = 'image'
            elif rec.name.endswith('medium'):
                rec.image_type = 'small_image'
            elif rec.name.endswith('small'):
                rec.image_type = 'thumbnail'

    @api.multi
    def comodel_data(self):
        return self.comodel_external_name, self.comodel_external_id


class MagentoIrAttachmentListener(Component):
    _name = 'magento.ir.attachment.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['ir.attachment']

    def on_record_write(self, record, fields=None):
        if any(field in fields for field in ['db_datas', 'store_fname']):
            for binding in record.magento_bind_ids:
                with binding.backend_id.work_on('magento.ir.attachment') as work:
                    adapter = work.component(usage='backend.adapter')
                    adapter.delete(binding.external_id, *binding.comodel_data())
                binding.external_id = False
                binding.with_delay().export_record()
