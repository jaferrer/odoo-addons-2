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

from odoo.tools import float_round

from odoo import fields, models, exceptions, _


class MrpBomLinePhantom(models.Model):
    _inherit = 'mrp.bom.line'

    type = fields.Selection([('normal', u"Normal"), ('phantom', u"Phantom")],
                            string=u"BoM Line Type", required=True, default='normal',
                            help=u"Phantom: this product line will not appear in the raw materials of manufacturing "
                                 u"orders, it will be directly replaced by the raw materials of its own BoM, "
                                 u"without triggering an extra manufacturing order.")


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def explode(self, product, quantity, picking_type=False):
        """
            Explodes the BoM and creates two lists with all the information you need: bom_done and line_done
            Quantity describes the number of times you need the BoM: so the quantity divided by the number created by
            the BoM and converted into its UoM
        """
        from collections import defaultdict

        graph = defaultdict(list)
        product_template_ids = set()

        def check_cycle(product_template_id, visited, rec_stack, graph):
            visited[product_template_id] = True
            rec_stack[product_template_id] = True
            for neighbour in graph[product_template_id]:
                if not visited[neighbour]:
                    if check_cycle(neighbour, visited, rec_stack, graph):
                        return True
                else:
                    return True
            rec_stack[product_template_id] = False
            return False

        boms_done = [(self, {'qty': quantity, 'product': product, 'original_qty': quantity, 'parent_line': False})]
        lines_done = []
        product_template_ids |= set([product.product_tmpl_id.id])

        bom_lines = [(bom_line, product, quantity, False) for bom_line in self.bom_line_ids]
        for bom_line in self.bom_line_ids:
            product_template_ids |= set([bom_line.product_id.product_tmpl_id.id])
            graph[product.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
        while bom_lines:
            current_line, current_product, current_qty, parent_line = bom_lines[0]
            bom_lines = bom_lines[1:]

            if current_line._skip_bom_line(current_product):
                continue

            line_quantity = current_qty * current_line.product_qty
            bom = self._bom_find(product=current_line.product_id,
                                 picking_type=picking_type or self.picking_type_id,
                                 company_id=self.company_id.id)
            if current_line.type == 'phantom' or bom.type == 'phantom':
                if not bom:
                    raise exceptions.UserError(_(u'BoM "%s" contains a phantom BoM line but the product "%s" does not '
                                                 u'have any BoM defined.') %
                                               (current_line.bom_id.display_name, current_line.product_id.display_name))
                converted_line_quantity = current_line.product_uom_id._compute_quantity(line_quantity / bom.product_qty,
                                                                                        bom.product_uom_id)
                bom_lines = [(line,
                              current_line.product_id,
                              converted_line_quantity,
                              current_line) for line in bom.bom_line_ids] + bom_lines
                for bom_line in bom.bom_line_ids:
                    graph[current_line.product_id.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
                    if bom_line.product_id.product_tmpl_id.id in product_template_ids and \
                            check_cycle(bom_line.product_id.product_tmpl_id.id,
                                        {key: False for key in product_template_ids},
                                        {key: False for key in product_template_ids}, graph):
                        raise exceptions.UserError(_('Recursion error!  A product with a Bill of Material should not '
                                                     'have itself in its BoM or child BoMs!'))
                    product_template_ids |= set([bom_line.product_id.product_tmpl_id.id])
                boms_done.append((bom, {'qty': converted_line_quantity,
                                        'product': current_product,
                                        'original_qty': quantity,
                                        'parent_line': current_line}))
            else:
                # We round up here because the user expects that if he has to consume a little more, the whole UOM unit
                # should be consumed.
                rounding = current_line.product_uom_id.rounding
                line_quantity = float_round(line_quantity, precision_rounding=rounding, rounding_method='UP')
                lines_done.append((current_line, {'qty': line_quantity,
                                                  'product': current_product,
                                                  'original_qty': quantity,
                                                  'parent_line': parent_line}))

        return boms_done, lines_done
