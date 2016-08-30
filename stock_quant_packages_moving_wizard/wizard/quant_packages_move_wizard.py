# -*- coding: utf8 -*-

#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, _, exceptions


class StockQuantPackageMove(models.TransientModel):
    _name = 'stock.quant.package.move'

    pack_move_items = fields.One2many(
        comodel_name='stock.quant.package.move_items', inverse_name='move_id',
        string="Packages")

    global_dest_loc = fields.Many2one(
        comodel_name='stock.location', string='Destination Location',
        required=True)

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking type', required=True)

    is_manual_op = fields.Boolean(string=u"Manual Operation")

    def default_get(self, cr, uid, fields, context=None):
        res = super(StockQuantPackageMove, self).default_get(
            cr, uid, fields, context=context)
        packages_ids = context.get('active_ids', [])
        if not packages_ids:
            return res
        packages_obj = self.pool['stock.quant.package']
        packages = packages_obj.browse(cr, uid, packages_ids, context=context)
        items = []
        loc = False
        for package in packages:
            loc = package.location_id
            if not package.parent_id and package.location_id:
                item = {
                    'package': package.id,
                    'source_loc': package.location_id.id,
                }
                items.append((0, 0, item))
        if loc:
            warehouses = self.pool['stock.warehouse'].browse(
                cr, uid, self.pool['stock.location'].get_warehouse(cr, uid, loc, context=context), context=context)
            if warehouses:
                res.update(picking_type_id=warehouses[0].picking_type_id.id)

        res.update(pack_move_items=items)
        return res

    @api.multi
    def do_detailed_transfer(self):
        self.ensure_one()
        quantsglob = self.env['stock.quant']
        packs = self.pack_move_items.filtered(
            lambda x: x.dest_loc != x.source_loc).mapped(lambda x: x.package)
        quantsglob |= self._determine_package_child_quants(packs)

        if quantsglob:
            result = quantsglob.move_to(self.global_dest_loc, self.picking_type_id, is_manual_op=self.is_manual_op)
            if self.is_manual_op:
                if not result:
                    raise exceptions.except_orm(_(u"error"), _("No line selected"))
                return {
                    'name': 'picking_form',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.picking',
                    'res_id': result[0].picking_id.id
                }
            else:
                return result

        return True

    def _determine_package_child_quants(self, packs):
        cumul = self.env['stock.quant']
        for item in packs:
            quants = item.mapped(lambda x: x.quant_ids)
            cumul |= quants
            packageChild = item.children_ids
            cumul |= self._determine_package_child_quants(packageChild)

        return cumul


class StockQuantPackageMoveItems(models.TransientModel):
    _name = 'stock.quant.package.move_items'
    _description = 'Picking wizard items'

    move_id = fields.Many2one(
        comodel_name='stock.quant.package.move', string='Package move')
    package = fields.Many2one(
        comodel_name='stock.quant.package', string='Quant package',
        domain=[('parent_id', '=', False), ('location_id', '!=', False)])
    source_loc = fields.Many2one(
        comodel_name='stock.location', string='Source Location')
    dest_loc = fields.Many2one(
        comodel_name='stock.location', string='Destination Location')

    @api.one
    @api.onchange('package')
    def onchange_quant(self):
        self.source_loc = self.package.location_id
