# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.tools import float_compare


class ProductLineMoveWizard(models.TransientModel):
    _name = 'product.move.wizard'

    move_to = fields.Selection([('location', "Location"),
                                ('package', "Package"),
                                ('execute_packops', "Execute packops for packages")],
                               string="Move to", required=True, default='location')
    global_dest_loc = fields.Many2one('stock.location', string="Destination Location")
    picking_type_id = fields.Many2one('stock.picking.type', string="Picking type")
    is_manual_op = fields.Boolean(string="Manual Operation")
    package_id = fields.Many2one('stock.quant.package', string="Package")
    quant_line_ids = fields.One2many('product.move.wizard.line', 'move_wizard_id', string="Products to move",
                                     domain=['|', ('product_id', '!=', False), ('package_id', '=', False)])
    package_line_ids = fields.One2many('product.move.wizard.line', 'move_wizard_id', string="Packages",
                                       domain=[('product_id', '=', False), ('package_id', '!=', False)])

    @api.model
    def default_get(self, fields):
        result = super(ProductLineMoveWizard, self).default_get(fields)
        line_ids = self.env.context.get('active_ids', [])
        lines = self.env['stock.product.line'].browse(line_ids)
        quant_lines = []
        package_lines = []
        for line in lines:
            line_dict = {
                'product_id': line.product_id.id,
                'product_name': line.product_id.display_name,
                'package_id': line.package_id and line.package_id.id or False,
                'package_name': line.package_id and line.package_id.display_name or False,
                'parent_id': line.parent_id and line.parent_id.id or False,
                'lot_id': line.lot_id and line.lot_id.id or False,
                'lot_name': line.lot_id and line.lot_id.display_name or False,
                'available_qty': line.qty,
                'qty': line.qty,
                'uom_id': line.uom_id and line.uom_id.id or False,
                'uom_name': line.uom_id and line.uom_id.display_name or False,
                'location_id': line.location_id.id,
                'location_name': line.location_id.display_name,
                'created_from_id': line.id,
            }
            if line.product_id or not line.package_id:
                quant_lines.append((0, 0, line_dict))
            else:
                package_lines.append((0, 0, line_dict))
        result.update(quant_line_ids=quant_lines)
        result.update(package_line_ids=package_lines)
        return result

    @api.onchange('quant_line_ids', 'package_line_ids')
    def onchange_is_manual_op(self):
        self.ensure_one()
        lines = self.quant_line_ids + self.package_line_ids
        self.is_manual_op = self.is_manual_op or lines.force_is_manual_op()

    @api.multi
    def move_to_location(self):
        lines = self.quant_line_ids + self.package_line_ids
        lines.check_quantities()
        lines.check_data_active()
        is_manual_op = self.is_manual_op or lines.force_is_manual_op()
        packages = self.env['stock.quant.package']
        for package_line in self.package_line_ids:
            packages |= package_line.package_id
        quants_to_move = packages.get_content()
        quants_to_move = self.env['stock.quant'].browse(quants_to_move)
        move_items = {}
        # Let's add package quants
        for quant in quants_to_move:
            move_items = quant.partial_move(move_items, quant.product_id, quant.qty)
        # Let's move quant lines
        for quant_line in self.quant_line_ids:
            domain = [('product_id', '=', quant_line.product_id.id),
                      ('location_id', '=', quant_line.location_id.id),
                      ('package_id', '=', quant_line.package_id and quant_line.package_id.id or False),
                      ('lot_id', '=', quant_line.lot_id and quant_line.lot_id.id or False),
                      ('product_id.uom_id', '=', quant_line.uom_id and quant_line.uom_id.id or False),
                      ('id', 'not in', quants_to_move.ids)]
            quants = self.env['stock.quant'].search(domain, order='in_date, qty')
            if quants:
                move_items = quants.partial_move(move_items, quant_line.product_id, quant_line.qty)
                quants_to_move |= quants
        if any([float_compare(quant.qty, 0, precision_rounding=quant.product_id.uom_id.rounding) < 0
                for quant in quants_to_move]):
            raise UserError(_("Impossible to move a negative quant"))
        result = quants_to_move.move_to(self.global_dest_loc, self.picking_type_id,
                                        move_items=move_items, is_manual_op=is_manual_op)
        if is_manual_op:
            if not result:
                raise UserError(_("No line selected"))
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

    @api.multi
    def move_to_package(self):
        packages = self.env['stock.quant.package']
        for package_line in self.package_line_ids:
            packages |= package_line.package_id
            if self.package_id.location_id and package_line.package_id.location_id and \
                    self.package_id.location_id != package_line.package_id.location_id:
                raise UserError(_("Impossible to move a package into a package of another location"))
        if packages:
            packages.write({'parent_id': self.package_id.id})
        quants_to_move = packages.get_content()
        quants = self.env['stock.quant']
        for quant_line in self.quant_line_ids:
            domain = [('product_id', '=', quant_line.product_id.id),
                      ('location_id', '=', quant_line.location_id.id),
                      ('package_id', '=', quant_line.package_id and quant_line.package_id.id or False),
                      ('lot_id', '=', quant_line.lot_id and quant_line.lot_id.id or False),
                      ('product_id.uom_id', '=', quant_line.uom_id and quant_line.uom_id.id or False),
                      ('id', 'not in', quants_to_move)]
            quants_line = self.env['stock.quant'].search(domain, order='in_date, qty')
            if self.package_id.location_id and \
                    any([quant.location_id != self.package_id.location_id for quant in quants_line]):
                raise UserError(_("Impossible to move a quant into a package of another location"))
            quants |= quants_line
        done_packages = self.env['stock.quant.package']
        for quant in quants:
            if not quant.package_id:
                quant.package_id = self.package_id
            elif quant.package_id not in done_packages:
                quants_package = quant.package_id.get_content()
                quants_package = self.env['stock.quant'].browse(quants_package)
                if any([sq not in quants for sq in quants_package]):
                    raise UserError(_("Impossible to move only a part of a package into another package"))
                quant.package_id.parent_id = self.package_id
                done_packages |= quant.package_id
        return self.env['stock.move']

    @api.multi
    def execute_packops_for_packages(self):
        packages = self.env['stock.quant.package']
        for package_line in self.package_line_ids:
            packages |= package_line.package_id
        if not packages:
            raise UserError("No package selected.")
        operations = self.env['stock.pack.operation'].search([('picking_id', '!=', False),
                                                              ('package_id', 'in', packages.ids)])
        operations.write({'processed_boolean': True})
        pickings_to_transfer = self.env['stock.picking']
        for operation in operations:
            if operation.picking_id not in pickings_to_transfer:
                operation.picking_id.pack_operation_product_ids.write({'qty_done': 0})
                operation.picking_id.pack_operation_pack_ids.filtered(lambda op: op not in operations). \
                    write({'processed_boolean': False})
                pickings_to_transfer |= operation.picking_id
        for picking in pickings_to_transfer:
            dict_transfer = picking.do_new_transfer()
            if dict_transfer:
                self.env[dict_transfer['res_model']].browse([dict_transfer['res_id']]).process()

    @api.multi
    def move_products(self):
        self.ensure_one()
        if self.move_to == 'location':
            return self.move_to_location()
        elif self.move_to == 'package':
            return self.move_to_package()
        elif self.move_to == 'execute_packops':
            return self.execute_packops_for_packages()


class ProductLineMoveWizardLine(models.TransientModel):
    _name = 'product.move.wizard.line'

    move_wizard_id = fields.Many2one('product.move.wizard', string="Move wizard", readonly=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    product_name = fields.Char(string="Product", readonly=True)
    package_id = fields.Many2one('stock.quant.package', string="Package", readonly=True)
    package_name = fields.Char(string="Package", readonly=True)
    parent_id = fields.Many2one('stock.quant.package', string="Parent package", readonly=True)
    lot_id = fields.Many2one('stock.production.lot', string="Lot", readonly=True)
    lot_name = fields.Char(string="Lot", readonly=True)
    available_qty = fields.Float(string="Available quantity", readonly=True)
    qty = fields.Float(string="Quantity to move")
    uom_id = fields.Many2one('product.uom', string="UOM", readonly=True)
    uom_name = fields.Char(string="UOM", readonly=True)
    location_id = fields.Many2one('stock.location', string="Location", readonly=True)
    location_name = fields.Char(string="Location", readonly=True)
    created_from_id = fields.Char(string="Created from ID", readonly=True)

    @api.multi
    def check_quantities(self):
        for rec in self:
            if rec.qty > rec.available_qty:
                raise UserError(_("The quantity to move must be lower or equal to the available quantity"))

    @api.multi
    def check_data_active(self):
        for rec in self:
            if rec.location_id and not rec.location_id.active:
                raise UserError(_("Impossible to move a quant from a not active location"))
            if rec.product_id and not rec.product_id.active:
                raise UserError(_("Impossible to move a quant of a not active product"))
            if rec.uom_id and not rec.uom_id.active:
                raise UserError(_("Impossible to move a quant of a not active UOM"))

    @api.multi
    def force_is_manual_op(self):
        # If the requested quantity is different from the available one, we force the user to validate
        # the picking manually.
        for rec in self:
            # Quant line with package
            if rec.product_id and rec.package_id:
                precision_rounding = rec.product_id.uom_id.rounding
                # Quant line without parent: force if the requested qty is different from the available qty
                if rec.package_id.children_ids:
                    return True
                if not rec.parent_id and float_compare(rec.qty, rec.available_qty,
                                                       precision_rounding=precision_rounding) != 0:
                    return True
                if self.env['stock.product.line'].search([('package_id', '=', rec.package_id.id),
                                                          ('product_id', '!=', False),
                                                          ('id', '!=', rec.created_from_id)]):
                    return True
            # Quant or package line with parent: force anyway
            if rec.parent_id:
                return True
        return False
