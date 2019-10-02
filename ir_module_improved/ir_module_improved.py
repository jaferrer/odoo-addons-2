# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import openerp
from openerp import models, fields
from openerp.tools import convert_file

old_convert_file = convert_file


def new_convert_file(cr, module, filename, idref, mode='update', noupdate=False, kind=None, report=None, pathname=None):
    final_mode = mode
    cr.execute("""SELECT *
FROM ir_module_module
WHERE state in ('installed', 'to upgrade') AND name = 'ir_module_improved'""")
    if cr.fetchall():
        cr.execute("""SELECT do_not_update_noupdate_data_when_install
FROM ir_module_module
WHERE name = %s""", (module,))
        result = cr.fetchone()
        if result and result[0] and mode == 'init':
            final_mode = 'update'
    old_convert_file(cr, module, filename, idref, mode=final_mode, noupdate=noupdate, kind=kind, report=report,
                     pathname=pathname)


openerp.tools.convert_file = new_convert_file


class IrModuleImproved(models.Model):
    _inherit = 'ir.module.module'

    do_not_update_noupdate_data_when_install = fields.Boolean(string=u"Do not update 'no update' data when installing "
                                                                     u"this module")

    @staticmethod
    def get_values_from_terp(terp):
        return {
            'description': terp.get('description', ''),
            'shortdesc': terp.get('name', ''),
            'author': terp.get('author', 'Unknown'),
            'maintainer': terp.get('maintainer', False),
            'contributors': ', '.join(terp.get('contributors', [])) or False,
            'website': terp.get('website', ''),
            'license': terp.get('license', 'AGPL-3'),
            'sequence': terp.get('sequence', 100),
            'application': terp.get('application', False),
            'auto_install': terp.get('auto_install', False),
            'icon': terp.get('icon', False),
            'summary': terp.get('summary', ''),
            'do_not_update_noupdate_data_when_install': terp.get('do_not_update_noupdate_data_when_install', False),
        }
