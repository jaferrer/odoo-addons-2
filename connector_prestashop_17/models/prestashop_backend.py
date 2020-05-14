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

from openerp import fields, models


class PrestashopBackend(models.Model):
    _inherit = 'prestashop.backend'

    def _select_versions(self):
        """ Available versions
        Can be inherited to add custom versions.
        """
        versions = super(PrestashopBackend, self)._select_versions()
        versions.append(('1.7', u">= 1.7"))
        return versions

    version = fields.Selection(
        _select_versions,
        string='Version',
        required=True)
    taxes_included = fields.Boolean(help="Check here if Prestahop send their prices tax included, which should not "
                                         "be the case most of the time.")
