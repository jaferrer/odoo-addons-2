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

import ftputil
from ftputil.file_transfer import RemoteFile

from odoo import models, fields, api


class FTPWizard(models.TransientModel):
    _name = 'ftp.wizard'
    _description = u"FTP Connection"

    """ This class' purpose is to offer a constant interface between odoo and a FTP/SFTP/... lib

    It allows to transparently change distant storage method without changing the module behaviour or function called
    """

    host = fields.Char(u"host", required=True)
    port = fields.Integer(u"Port", required=True, default=21)
    username = fields.Char(u"Username", required=True)
    password = fields.Char(u"Password")

    def join(self, ftp, *paths):
        """ Join several ftp paths or filenames into one single path

        :param ftp: ftp handle
        :param paths: paths to join
        :return: resulting path (str)
        """
        return ftp.path.join(*map(str, paths))

    def split(self, ftp, path):
        """ Splits a path into several directories/file names

        :param ftp: ftp handle
        :param path: path to split
        :return: list of directories and file
        """
        head = path
        paths = []
        while head and head != '/':
            head, tail = ftp.path.split(head)
            paths.insert(0, tail)
        return paths

    @api.multi
    def get_conn(self):
        """ Return a ftp connection corresponding to the current record parameters """
        self.ensure_one()
        return ftputil.FTPHost(self.host, self.username, self.password)

    def listdir(self, ftp, path=None):
        """ List content of a certain path on ftp

        :param ftp: ftp handle
        :param path: path to the directory to list. If None, current directory will be used
        :return: list of files/directories contained in the directory
        """
        path = path or self.cwd(ftp)
        return ftp.listdir(path)

    def mkdir(self, ftp, path):
        """ Create directories to make all this path exist

        :param ftp: ftp handle
        :param path: path to create
        """
        ftp.makedirs(path)

    def get(self, ftp, lfobj, path):
        """ Download a file

        :param ftp: ftp handle
        :param lfobj: file object to write copy the distant file content in
        :param path: path to the file on the ftp server
        """
        rfile = RemoteFile(ftp, ftputil.tool.as_unicode(path), 'rb')
        rfobj = rfile.fobj()
        # We must use a lower level function than copy_file because it was closing the BytesIO buffer
        ftputil.file_transfer.copyfileobj(rfobj, lfobj)
        rfobj.close()

    def put(self, ftp, lfobj, path):
        """ Upload a file

        :param ftp; ftp handle
        :param lfobj: file object to read data from
        :param path: path to the destination on the ftp server
        """
        rfile = RemoteFile(ftp, ftputil.tool.as_unicode(path), 'wb')
        rfobj = rfile.fobj()
        # We must use a lower level function than copy_file because it was closing the BytesIO buffer
        ftputil.file_transfer.copyfileobj(lfobj, rfobj)
        rfobj.close()

    def chdir(self, ftp, path):
        """ Change current directory on the FTP server """
        ftp.chdir(path)

    def cwd(self, ftp):
        """ Return the current working directory on the FTP server """
        return ftp.getcwd()

    def move(self, ftp, old_path, new_path):
        """ Moves a file on the FTP server from one path to another"""
        ftp.rename(old_path, new_path)

    def close(self, ftp):
        """ Close FTP connexion """
        ftp.close()
