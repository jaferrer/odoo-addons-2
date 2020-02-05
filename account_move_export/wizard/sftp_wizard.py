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

from odoo import models, api


class STFPWizard(models.Model):
    _inherit = 'ftp.wizard'
    _name = 'sftp.wizard'
    _description = u"SFTP Connection"

    def join(self, sftp, *paths):
        """ Join several sftp paths or filenames into one single path

        :param sftp: sftp handle
        :param paths: paths to join
        :return: resulting path (str)
        """
        pass

    def split(self, sftp, path):
        """ Splits a path into several directories/file names

        :param sftp: sftp handle
        :param path: path to split
        :return: list of directories and file
        """
        pass

    @api.multi
    def get_conn(self):
        """ Return a sftp connection corresponding to the current record parameters """
        pass

    def listdir(self, sftp, path=None):
        """ List content of a certain path on sftp

        :param sftp: sftp handle
        :param path: path to the directory to list. If None, current directory will be used
        :return: list of files/directories contained in the directory
        """
        pass

    def mkdir(self, sftp, path):
        """ Create directories to make all this path exist

        :param sftp: sftp handle
        :param path: path to create
        """
        pass

    def get(self, sftp, lfobj, path):
        """ Download a file

        :param sftp: sftp handle
        :param lfobj: file object to write copy the distant file content in
        :param path: path to the file on the sftp server
        """
        pass

    def put(self, sftp, lfobj, path):
        """ Upload a file

        :param sftp; sftp handle
        :param lfobj: file object to read data from
        :param path: path to the destination on the sftp server
        """
        pass

    def chdir(self, sftp, path):
        """ Change current directory on the SFTP server """
        pass

    def cwd(self, sftp):
        """ Return the current working directory on the SFTP server """
        pass

    def move(self, sftp, old_path, new_path):
        """ Moves a file on the SFTP server from one path to another"""
        pass

    def close(self, sftp):
        """ Close SSFTP connexion """
        pass
