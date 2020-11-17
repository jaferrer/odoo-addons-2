# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import logging

from odoo.exceptions import AccessError

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class S3ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    module_odoo_s3 = fields.Boolean("Connect filestore to an extra S3 storage")
    s3_host = fields.Char('S3 Host', config_parameter='odoo_s3.s3_host')
    s3_access_key = fields.Char('S3 Access Key', config_parameter='odoo_s3.s3_access_key')
    s3_secret_key = fields.Char('S3 Secret Key', config_parameter='odoo_s3.s3_secret_key')
    s3_region = fields.Char('S3 Region', config_parameter='odoo_s3.s3_region')
    s3_bucket = fields.Char('Bucket Name', config_parameter='odoo_s3.s3_bucket')
    s3_load = fields.Boolean('Load S3 with existing filestore?', help="If you check this option, when you apply",
                             config_parameter='odoo_s3.s3_load', inverse='_set_s3_load')

    def _set_s3_load(self):
        if not self.s3_load:
            return
        try:
            self.env['ir.attachment']._connect_to_S3_bucket()
            self.env['ir.attachment'].sudo()._copy_filestore_to_s3()
        except Exception as e:
            raise AccessError(
                _('Error accessing the bucket \"%s\" : %s.') % (self.s3_bucket, e))

    def test_move_filestore_to_s3(self):
        for wiz in self:
            try:
                s3_bucket = self.env['ir.attachment']._connect_to_S3_bucket()
                bucket_name = self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_bucket')
                if s3_bucket.bucket_exists(bucket_name):
                    _logger.info("S3 bucket connection successful %s", bucket_name)
                    continue
                raise Exception('Bucket does not exist')
            except Exception as e:
                raise AccessError(
                    _('Error accessing the bucket "%s": %s.\n'
                      'Please fix the "S3 Storage" settings') % (wiz.s3_bucket, e))
