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
import base64
import logging
import os

import pysftp
import paramiko
from paramiko import ECDSAKey, DSSKey, RSAKey, Ed25519Key

from odoo import models, fields, api, _ as _t


_logger = logging.getLogger(__name__)


class STFPWizard(models.Model):
    _inherit = 'ftp.wizard'
    _name = 'sftp.wizard'
    _description = u"SFTP Connection"

    key_type = fields.Char(u"Key type")
    key_str = fields.Char(u"Key")

    def join(self, sftp, *paths):
        """ Join several sftp paths or filenames into one single path

        :param sftp: sftp handle
        :param paths: paths to join
        :return: resulting path (str)
        """
        return os.path.join(*map(unicode, paths))

    def split(self, sftp, path):
        """ Splits a path into several directories/file names

        :param sftp: sftp handle
        :param path: path to split
        :return: list of directories and file
        """
        head = path
        paths = []
        while head and head != '/':
            head, tail = os.path.split(head)
            paths.insert(0, tail)
        return paths

    @api.multi
    def get_conn(self):
        """ Return a sftp connection corresponding to the current record parameters """
        key_type = self.key_type
        key = None

        if key_type:
            bkey = base64.decodestring(self.key_str)
            if key_type == "ssh-rsa":
                key = RSAKey(data=bkey)
            elif key_type == "ssh-dss":
                key = DSSKey(data=bkey)
            elif key_type in ECDSAKey.supported_key_format_identifiers():
                key = ECDSAKey(data=bkey, validate_point=False)
            elif key_type == "ssh-ed25519":
                key = Ed25519Key(data=bkey)

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = paramiko.hostkeys.HostKeys()
        if key:
            cnopts.hostkeys.add(self.host, key_type, key)
        else:
            cnopts.hostkeys = None
            _logger.warning(_t(u"Running in insecure mode : any host can pretend to be the SFTP server"))
        return pysftp.Connection(host=self.host, port=self.port, username=self.username, password=self.password,
                                 cnopts=cnopts)

    def listdir(self, sftp, path=None):
        """ List content of a certain path on sftp

        :param sftp: sftp handle
        :param path: path to the directory to list. If None, current directory will be used
        :return: list of files/directories contained in the directory
        """
        return sftp.listdir(path or '.')

    def mkdir(self, sftp, path):
        """ Create directories to make all this path exist

        :param sftp: sftp handle
        :param path: path to create
        """
        sftp.makedirs(path)

    def get(self, sftp, lfobj, path):
        """ Download a file

        :param sftp: sftp handle
        :param lfobj: file object to write copy the distant file content in
        :param path: path to the file on the sftp server
        """
        sftp.getfo(path, lfobj)

    def put(self, sftp, lfobj, path):
        """ Upload a file

        :param sftp; sftp handle
        :param lfobj: file object to read data from
        :param path: path to the destination on the sftp server
        """
        sftp.putfo(lfobj, path)

    def chdir(self, sftp, path):
        """ Change current directory on the SFTP server """
        sftp.cwd(path)

    def cwd(self, sftp):
        """ Return the current working directory on the SFTP server """
        return sftp.pwd

    def move(self, sftp, old_path, new_path):
        """ Moves a file on the SFTP server from one path to another"""
        sftp.rename(old_path, new_path)

    def close(self, sftp):
        """ Close SFTP connexion """
        sftp.close()
