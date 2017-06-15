# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields

class IrAction(models.Model):
    _inherit = 'ir.actions.report.xml'

    type_multi_print = fields.Selection((
        ('file', u"Fichier Unique"),
        ('pdf', u"Pdf Unique page par page"),
        ('zip', u"Conteneur Zip")
    ), u"Type de post traitement lors de l'impression mutliple", default='file')

    name_eval_report = fields.Char(u"expression for the name of the report")


