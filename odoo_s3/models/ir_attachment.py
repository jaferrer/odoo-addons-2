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
# pylint: disable=W0703

import base64
import logging
import os
from cStringIO import StringIO

from minio import Minio

from odoo import api, models, exceptions
from odoo.conf import server_wide_modules

_logger = logging.getLogger(__name__)


class S3Attachment(models.Model):
    """Extends ir.attachment to implement the S3 storage engine
    """
    _inherit = "ir.attachment"
    _s3_bucket = False

    def _get_s3_bucket_name(self):
        return os.environ.get('ODOO_S3_BUCKET', self.env['ir.config_parameter'].sudo().get_param('odoo_s3.s3_bucket'))

    def _storage(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        at_least_one_s3_param_missing = not get_param('odoo_s3.s3_host') or \
            not get_param('odoo_s3.s3_access_key') or \
            not get_param('odoo_s3.s3_secret_key') or \
            not get_param('odoo_s3.s3_region') or \
            not get_param('odoo_s3.s3_bucket')
        if 'odoo_s3' not in server_wide_modules or at_least_one_s3_param_missing:
            return super(S3Attachment, self)._storage()
        return self.env.context.get('force_attachment_storage', 's3')

    def _connect_to_S3_bucket(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        host = os.environ.get('ODOO_S3_HOST', get_param('odoo_s3.s3_host'))
        access_key = os.environ.get('ODOO_S3_ACCESS_KEY', get_param('odoo_s3.s3_access_key'))
        secret_key = os.environ.get('ODOO_S3_SECRET_KEY', get_param('odoo_s3.s3_secret_key'))
        region = os.environ.get('ODOO_S3_REGION', get_param('odoo_s3.s3_region'))
        bucket_name = self._get_s3_bucket_name()

        session = Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )

        if not session.bucket_exists(bucket_name):
            session.make_bucket(bucket_name, location=region)
        return session

    @api.model
    def _file_read(self, fname, bin_size=False):
        if self._storage() != 's3':
            # storage is not as s3 type
            return super(S3Attachment, self)._file_read(fname, bin_size=bin_size)

        res = super(S3Attachment, self)._file_read(fname, bin_size=bin_size)
        if res:
            return res

        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
        except Exception as e:
            _logger.error('S3: _file_read Was not able to connect to S3 (%s)', e)

        res = ''
        s3_key = None
        bucket_name = self._get_s3_bucket_name()
        key = '%s/%s' % (self.env.registry.db_name, fname)
        bin_data = ''
        try:
            s3_key = self._s3_bucket.get_object(bucket_name, key)
            bin_data = s3_key.read()
            res = base64.b64encode(bin_data)
            _logger.debug('S3: _file_read read %s:%s from bucket successfully', bucket_name, key)

        except Exception as e:
            _logger.error('S3: _file_read was not able to read from S3 (%s): %s', key, e)

        finally:
            if s3_key:
                s3_key.close()
                s3_key.release_conn()
        if res:
            # Try to cache file locally
            try:
                self.with_context(force_attachment_storage='file')._file_write(res, self._compute_checksum(bin_data))
            except Exception as e:
                _logger.error('S3: unable to cache %s file locally: %s', key, e)
        return res

    @api.model
    def _file_write(self, value, checksum):
        if self._storage() != 's3':
            # storage is not as s3 type
            _logger.debug('S3: _file_write bypass to filesystem storage')
            return super(S3Attachment, self)._file_write(value, checksum)
        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
        except Exception as e:
            _logger.error('S3: _file_write was not able to connect (%s)', e)
            return super(S3Attachment, self)._file_write(value, checksum)

        bin_value = value.decode('base64')
        fname, _ = self._get_path(bin_value, checksum)
        bucket_name = self._get_s3_bucket_name()
        key = '%s/%s' % (self.env.registry.db_name, fname)
        s3_key = None

        try:
            self._s3_bucket.put_object(bucket_name, key, StringIO(bin_value), len(bin_value))
            _logger.debug('S3: _file_write %s:%s was successfully uploaded', bucket_name, key)
        except Exception as e:
            _logger.error('S3: _file_write was not able to write (%s): %s', key, e)
            raise exceptions.UserError(u"_file_write was not able to write (%s): %s" % (key, e))
        finally:
            if s3_key:
                s3_key.close()
                s3_key.release_conn()
        # Returning the file name
        return fname

    @api.model
    def _file_gc_s3(self):
        if self._storage() != 's3':
            return

        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
            _logger.debug('S3: _file_gc_s3 connected Sucessfuly')
        except Exception as e:
            _logger.error('S3: _file_gc_s3 was not able to connect (%s)', e)
            return False

        # Continue in a new transaction. The LOCK statement below must be the
        # first one in the current transaction, otherwise the database snapshot
        # used by it may not contain the most recent changes made to the table
        # ir_attachment! Indeed, if concurrent transactions create attachments,
        # the LOCK statement will wait until those concurrent transactions end.
        # But this transaction will not see the new attachements if it has done
        # other requests before the LOCK (like the method _storage() above).
        cr = self._cr
        cr.commit()

        # prevent all concurrent updates on ir_attachment while collecting!
        cr.execute("LOCK ir_attachment IN SHARE MODE")

        bucket_name = self._get_s3_bucket_name()
        real_key_name = check_key_name = ''
        removed = 0
        checklist = {}
        prefix = '%s/checklist/' % self.env.registry.db_name
        # retrieve the file names from the checklist
        for s3_key_gc in self._s3_bucket.list_objects(bucket_name, prefix=prefix, recursive=True):
            if not s3_key_gc.is_dir:
                fname = s3_key_gc.object_name[len(prefix):]
                real_key_name = '%s/%s' % (self.env.registry.db_name, fname)
                checklist[fname] = (real_key_name, s3_key_gc.object_name)

        # determine which files to keep among the checklist
        whitelist = set()
        for names in cr.split_for_in_conditions(checklist):
            cr.execute("SELECT store_fname FROM ir_attachment WHERE store_fname IN %s", [names])
            whitelist.update('%s/%s' % (self.env.registry.db_name, row[0]) for row in cr.fetchall())

        # remove garbage files, and clean up checklist
        for real_key_name, check_key_name in checklist.values():
            if real_key_name not in whitelist:
                try:
                    self._s3_bucket.remove_object(bucket_name, real_key_name)
                    removed += 1
                    _logger.debug('S3: _file_gc_s3 deleted %s:%s successfully', bucket_name, real_key_name)
                except Exception as e:
                    _logger.error('S3: _file_gc_s3 was not able to gc (%s:%s) : %s', bucket_name, real_key_name, e)
            try:
                self._s3_bucket.remove_object(bucket_name, check_key_name)
            except Exception as e:
                _logger.error('S3: _file_gc_s3 was not able to gc %s check_key %s: %s', bucket_name, check_key_name, e)

        # commit to release the lock
        cr.commit()
        _logger.info("S3: filestore gc %d checked, %d removed", len(checklist), removed)
        self.with_context(force_attachment_storage='file')._file_gc()

    def _mark_for_gc(self, fname):
        """ We will mark for garbage collection in both s3 and filesystem
        Just the garbage collection in s3 will move to trash and not delete"""
        if self._storage() != 's3':
            return super(S3Attachment, self)._mark_for_gc(fname)

        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
            _logger.debug('S3: File mark as gc. Connected successfully')
        except Exception as e:
            _logger.error('S3: File mark as gc. Was not able to connect (%s)', e)
            raise exceptions.UserError(u"File mark as gc. Was not able to connect (%s)" % e)

        new_key = '%s/checklist/%s' % (self.env.registry.db_name, fname)
        bucket_name = self._get_s3_bucket_name()
        try:
            # Just create an empty file
            self._s3_bucket.put_object(bucket_name, new_key, StringIO(), 0)
            _logger.debug('S3: _mark_for_gc %s:%s marked for garbage collection', bucket_name, new_key)
        except Exception:
            _logger.error('S3: _mark_for_gc Was not able to save key:%s', new_key)
            raise exceptions.UserError(u"_mark_for_gc Was not able to save key: %s" % new_key)
        self.with_context(force_attachment_storage='file')._mark_for_gc(fname)

    def _copy_filestore_to_s3(self):
        with api.Environment.manage():
            try:
                if self._run_copy_filestore_to_s3():
                    _logger.info('S3: filestore copied to S3 successfully')
                raise Exception('Storage is not S3 or already loaded to S3.')
            except Exception as e:
                _logger.info('S3: filestore copy to S3 aborted! %s', e)
            return {}

    @api.model
    def _run_copy_filestore_to_s3(self):
        is_copied = self.env['ir.config_parameter'].sudo().get_param('ir_attachment.location_s3_copied_to', False)
        if self._storage() != 's3' or is_copied:
            return False

        db_name = self.env.registry.db_name
        full_path = self._full_path('')
        bucket_name = self._get_s3_bucket_name()

        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
            _logger.debug('S3: Copy filestore to S3. Connected successfully')
        except Exception as e:
            _logger.error('S3: Copy filestore to S3. Was not able to connect (%s), gonna try other filestore', e)

        for root, _, files in os.walk(full_path):
            for file_name in files:
                path = os.path.join(root, file_name)
                self._s3_bucket.fput_object(bucket_name, '%s/%s' % (db_name, path[len(full_path):]), path)
                _logger.debug('S3: Copy filestore to S3. Loading file %s to %s/%s',
                              db_name, path, path[len(full_path):])
        self.env['ir.config_parameter'].sudo().set_param('ir_attachment.location_s3_copied_to %s' % bucket_name,
                                                         groups=['base.group_system'])
        return True

    @api.multi
    def check_s3_filestore(self):
        """This command is here for being trigger using odoo shell:

        e.g.:

        $> a, b = env['ir.attachment'].search([]).check_s3_filestore()
        $> filter(lambda x: x['s3_lost']==True, a)
        $> print b # will show totals
        $> env.cr.commit() # need to do this to update the table s3_lost field to know if something is lost

        """
        if self._storage() != 's3':
            return
        try:
            if not self._s3_bucket:
                self._s3_bucket = self._connect_to_S3_bucket()
            _logger.debug('S3: _file_gc_s3 connected successfully')
        except Exception:
            _logger.error('S3: _file_gc_s3 was not able to connect (%s)')
            return False

        status_res = []
        totals = {
            'lost_count': 0,
        }
        bucket_name = self._get_s3_bucket_name()
        for att in self:
            status = {'name': att.name, 'fname': att.store_fname, 's3_lost': False}
            s3_key = None
            try:
                if not att.store_fname:
                    raise Exception('There is no store_fname')
                s3_key = self._s3_bucket.get_object(bucket_name, att.store_fname)
                if s3_key.status == 404:
                    status['s3_lost'] = True
                    totals['lost_count'] += 1

                _logger.debug('S3: check_s3_filestore read %s:%s from bucket successfully',
                              bucket_name, att.store_fname)

            except Exception as e:
                status['error'] = e.message
            finally:
                if s3_key:
                    s3_key.close()
                    s3_key.release_conn()
            status_res.append(status)

        return status_res, totals
