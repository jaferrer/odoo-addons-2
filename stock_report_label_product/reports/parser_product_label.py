# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models


class Parser(models.AbstractModel):
    _name = 'report.etiquettes_produit'
    _inherit = 'report.report_aeroo.abstract'

    def _identifiants_produits_produits(self, object):
        liste_produits = []
        pp_obj = self.pool.get('product.product')
        pp_ids = pp_obj.search(self.cr, self.uid, [('product_tmpl_id', '=', object.id)])
        for pp in pp_obj.browse(self.cr, self.uid, pp_ids):
            if pp.product_ident_id:
                dictionnaire = {
                    'designation_produit': pp.name,
                    'code_barre': pp.product_ident_id.name,
                    'last': True
                }
                liste_produits.append(dictionnaire)
        return liste_produits

    def complex_report(self, docids, data, report, ctx):
        ctx = dict(ctx) or {}
        ctx.update({
            'identifiants_produits_produits': self._identifiants_produits_produits,
        })
        return super(Parser, self).complex_report(docids, data, report, ctx)
