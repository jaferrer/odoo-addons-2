# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError

import logging

_logger = logging.getLogger(__name__)


class S3ResConfig(models.TransientModel):
    _inherit = 'base.config.settings'

    s3_host = fields.Char('S3 Host')
    s3_access_key = fields.Char('S3 Access Key')
    s3_secret_key = fields.Char('S3 Secret Key')
    s3_region = fields.Char('S3 Region')
    s3_bucket = fields.Char('Bucket Name')
    s3_load = fields.Boolean('Load S3 with existing filestore?', help="If you check this option, when you apply")

    @api.model
    def get_default_s3_host(self, fields):
        return {
            's3_host': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_host')
        }

    @api.multi
    def set_s3_host(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_host', self.s3_host)

    @api.model
    def get_default_s3_access_key(self, fields):
        return {
            's3_access_key': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_access_key')
        }

    @api.multi
    def set_s3_access_key(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_access_key', self.s3_access_key)

    @api.model
    def get_default_s3_secret_key(self, fields):
        return {
            's3_secret_key': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_secret_key')
        }

    @api.multi
    def set_s3_secret_key(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_secret_key', self.s3_secret_key)

    @api.model
    def get_default_s3_region(self, fields):
        return {
            's3_region': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_region')
        }

    @api.multi
    def set_s3_region(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_region', self.s3_region)

    @api.model
    def get_default_s3_bucket(self, fields):
        return {
            's3_bucket': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_bucket')
        }

    @api.multi
    def set_s3_bucket(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_bucket', self.s3_bucket)

    @api.model
    def get_default_s3_load(self, fields):
        return {
            's3_load': self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_load')
        }

    @api.multi
    def set_s3_load(self):
        self.env['ir.config_parameter'].sudo().set_param('odoo_s3.s3_load', self.s3_load)
        if self.s3_load:
            try:
                self.env['ir.attachment']._connect_to_S3_bucket()
                self.env['ir.attachment'].sudo()._copy_filestore_to_s3()
            except Exception as e:
                raise AccessError(
                    _('Error accessing the bucket \"%s\" : %s.') % (self.s3_bucket, e))

    @api.multi
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
