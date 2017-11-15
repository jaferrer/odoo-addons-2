# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models
from openerp.addons.report_aeroo.ExtraFunctions import ExtraFunctions

class FixExtrafunction(models.BaseModel):
    _name = 'fix.extrafunction'
    _auto = False

    def _register_hook(self, cr):
        def _new_translate_text(self, source):
            trans_obj = self.registry['ir.translation']
            trans = trans_obj.search_read(self.cr, self.uid,
                                          fields=['value'],
                                          domain=[
                                              ('res_id', '=', self.report_id), ('type', '=', 'report'),
                                              ('src', '=', source),
                                              ('lang', '=', self.context['lang'] or self.context['user_lang'])
                                          ],
                                          limit=1,
                                          order='sequence desc')
            trans_value = trans and trans[0] and trans[0]['value'] or False
            if not trans_value:
                trans_obj.create(self.cr, self.uid,
                                 {'src': source, 'type': 'report', 'lang': self._get_lang(), 'res_id': self.report_id,
                                  'name': 'ir.actions.report.xml'})
            return trans_value or source

        ExtraFunctions._translate_text = _new_translate_text
        return super(FixExtrafunction, self)._register_hook(cr)
