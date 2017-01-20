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

import time
from datetime import datetime

from openerp import models, api, fields, osv, _


class FluxTenduStockPacOPeration(models.Model):
    _inherit = 'stock.move'

    def check_tracking_product(self, cr, uid, product, lot_id, location, location_dest, context=None):
        check = False
        if product.track_all and not location_dest.usage == 'inventory':
            check = True
        elif product.track_incoming and location.usage in (
        'supplier', 'transit', 'inventory') and location_dest.usage == 'internal':
            check = True
        elif product.track_outgoing and location_dest.usage in ('customer', 'transit') and location.usage == 'internal':
            check = True
        if check and not lot_id:
            raise osv.except_osv(_('Warning!'),
                                 _('You must assign a serial number for the product %s') % (product.name))


class FluxTenduStockPacOPeration(models.Model):
    _inherit = 'stock.pack.operation'

    processed = fields.Selection([('true','Yes'), ('false','No')],'Has been processed?', required=True)

    def action_drop_down(self, cr, uid, ids, context=None):
        ''' Used by barcode interface to say that pack_operation has been moved from src location
            to destination location, if qty_done is less than product_qty than we have to split the
            operation in two to process the one with the qty moved
        '''
        processed_ids = []
        move_obj = self.pool.get("stock.move")
        for pack_op in self.browse(cr, uid, ids, context=None):
            if pack_op.product_id and pack_op.location_id and pack_op.location_dest_id:
                lot_id = pack_op.pack_lot_ids and pack_op.pack_lot_ids[0].lot_id.id or False
                #move_obj.check_tracking_product(cr, uid, pack_op.product_id, lot_id, pack_op.location_id,
                #                                pack_op.location_dest_id, context=context)
            op = pack_op.id
            if pack_op.qty_done < pack_op.product_qty:
                # we split the operation in two
                op = self.copy(cr, uid, pack_op.id, {'product_qty': pack_op.qty_done, 'qty_done': pack_op.qty_done},
                               context=context)
                self.write(cr, uid, [pack_op.id],
                           {'product_qty': pack_op.product_qty - pack_op.qty_done, 'qty_done': 0}, context=context)
            processed_ids.append(op)
        self.write(cr, uid, processed_ids, {'processed': 'true'}, context=context)

    def _search_and_increment(self, cr, uid, picking_id, domain, filter_visible=False, visible_op_ids=False, increment=True,
                              context=None):
        '''Search for an operation with given 'domain' in a picking, if it exists increment the qty (+1) otherwise create it

        :param domain: list of tuple directly reusable as a domain
        context can receive a key 'current_package_id' with the package to consider for this operation
        returns True
        '''
        if context is None:
            context = {}

        # if current_package_id is given in the context, we increase the number of items in this package
        package_clause = [('result_package_id', '=', context.get('current_package_id', False))]
        existing_operation_ids = self.search(cr, uid, [('picking_id', '=', picking_id)] + domain + package_clause,
                                             context=context)
        todo_operation_ids = []
        if existing_operation_ids:
            if filter_visible:
                todo_operation_ids = [val for val in existing_operation_ids if val in visible_op_ids]
            else:
                todo_operation_ids = existing_operation_ids
        if todo_operation_ids:
            # existing operation found for the given domain and picking => increment its quantity
            operation_id = todo_operation_ids[0]
            op_obj = self.browse(cr, uid, operation_id, context=context)
            qty = op_obj.qty_done
            if increment:
                qty += 1
            else:
                qty -= 1 if qty >= 1 else 0
                if qty == 0 and op_obj.product_qty == 0:
                    # we have a line with 0 qty set, so delete it
                    self.unlink(cr, uid, [operation_id], context=context)
                    return False
            self.write(cr, uid, [operation_id], {'qty_done': qty}, context=context)
        else:
            # no existing operation found for the given domain and picking => create a new one
            picking_obj = self.pool.get("stock.picking")
            picking = picking_obj.browse(cr, uid, picking_id, context=context)
            values = {
                'picking_id': picking_id,
                'product_qty': 0,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'qty_done': 1,
            }
            for key in domain:
                var_name, dummy, value = key
                uom_id = False
                if var_name == 'product_id':
                    uom_id = self.pool.get('product.product').browse(cr, uid, value, context=context).uom_id.id
                update_dict = {var_name: value}
                if uom_id:
                    update_dict['product_uom_id'] = uom_id
                values.update(update_dict)
            operation_id = self.create(cr, uid, values, context=context)
        return operation_id


class FluxTenduStockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def get_next_picking_for_ui(self):
        """ returns the next pickings to process. Used in the barcode scanner UI"""
        if self.env.context is None:
            context = {}
        else:
            context = self.env.context

        domain = [('state', 'in', ('assigned', 'partially_available'))]
        if context.get('default_picking_type_id'):
            domain.append(('picking_type_id', '=', context['default_picking_type_id']))
        return self.search(domain).ids

    @api.multi
    def action_done_from_ui(self):
        """ called when button 'done' is pushed in the barcode scanner UI """
        # write qty_done into field product_qty for every package_operation before doing the transfer
        self.ensure_one()
        pack_op_obj = self.env['stock.pack.operation']
#        for operation in self.pack_operation_ids:
#            operation.with_context(no_recompute=True).write({'product_qty': operation.qty_done})
        self.do_transfer()
        # return id of next picking to work on
        return self.get_next_picking_for_ui()

    @api.model
    def check_group_lot(self):
        """ This function will return true if we have the setting to use lots activated. """
        return self.env['res.users'].has_group('stock.group_production_lot')

    @api.model
    def check_group_pack(self):
        """ This function will return true if we have the setting to use package activated. """
        return self.env['res.users'].has_group('stock.group_tracking_lot')

    def process_product_id_from_ui(self, cr, uid, picking_id, product_id, op_id, increment=True, context=None):
        return self.pool.get('stock.pack.operation')._search_and_increment(cr, uid, picking_id,
                                                                           [('product_id', '=', product_id),
                                                                            ('id', '=', op_id)], increment=increment,
                                                                           context=context)

    def process_barcode_from_ui(self, cr, uid, picking_id, barcode_str, visible_op_ids, context=None):
        '''This function is called each time there barcode scanner reads an input'''
        lot_obj = self.pool.get('stock.production.lot')
        package_obj = self.pool.get('stock.quant.package')
        product_obj = self.pool.get('product.product')
        stock_operation_obj = self.pool.get('stock.pack.operation')
        stock_location_obj = self.pool.get('stock.location')
        answer = {'filter_loc': False, 'operation_id': False}
        # check if the barcode correspond to a location
        matching_location_ids = stock_location_obj.search(cr, uid, [('barcode', '=', barcode_str)], context=context)
        if matching_location_ids:
            # if we have a location, return immediatly with the location name
            location = stock_location_obj.browse(cr, uid, matching_location_ids[0], context=None)
            answer['filter_loc'] = stock_location_obj._name_get(cr, uid, location, context=None)
            answer['filter_loc_id'] = matching_location_ids[0]
            return answer
        # check if the barcode correspond to a product
        matching_product_ids = product_obj.search(cr, uid, ['|', ('barcode', '=', barcode_str),
                                                            ('default_code', '=', barcode_str)], context=context)
        if matching_product_ids:
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id,
                                                              [('product_id', '=', matching_product_ids[0])],
                                                              filter_visible=True, visible_op_ids=visible_op_ids,
                                                              increment=True, context=context)
            answer['operation_id'] = op_id
            return answer
        # check if the barcode correspond to a lot
        matching_lot_ids = lot_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
        if matching_lot_ids:
            lot = lot_obj.browse(cr, uid, matching_lot_ids[0], context=context)
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id,
                                                              [('product_id', '=', lot.product_id.id),
                                                               ('lot_id', '=', lot.id)], filter_visible=True,
                                                              visible_op_ids=visible_op_ids, increment=True,
                                                              context=context)
            answer['operation_id'] = op_id
            return answer
        # check if the barcode correspond to a package
        matching_package_ids = package_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
        if matching_package_ids:
            op_id = stock_operation_obj._search_and_increment(cr, uid, picking_id,
                                                              [('package_id', '=', matching_package_ids[0])],
                                                              filter_visible=True, visible_op_ids=visible_op_ids,
                                                              increment=True, context=context)
            answer['operation_id'] = op_id
            return answer
        return answer

    @api.cr_uid_ids_context
    def action_pack(self, cr, uid, picking_ids, operation_filter_ids=None, context=None):
        """ Create a package with the current pack_operation_ids of the picking that aren't yet in a pack.
        Used in the barcode scanner UI and the normal interface as well.
        operation_filter_ids is used by barcode scanner interface to specify a subset of operation to pack"""
        if operation_filter_ids == None:
            operation_filter_ids = []
        stock_operation_obj = self.pool.get('stock.pack.operation')
        package_obj = self.pool.get('stock.quant.package')
        stock_move_obj = self.pool.get('stock.move')
        package_id = False
        for picking_id in picking_ids:
            operation_search_domain = [('picking_id', '=', picking_id), ('result_package_id', '=', False)]
            if operation_filter_ids != []:
                operation_search_domain.append(('id', 'in', operation_filter_ids))
            operation_ids = stock_operation_obj.search(cr, uid, operation_search_domain, context=context)
            pack_operation_ids = []
            if operation_ids:
                for operation in stock_operation_obj.browse(cr, uid, operation_ids, context=context):
                    # If we haven't done all qty in operation, we have to split into 2 operation
                    op = operation
                    if (operation.qty_done < operation.product_qty):
                        new_operation = stock_operation_obj.copy(cr, uid, operation.id,
                                                                 {'product_qty': operation.qty_done,
                                                                  'qty_done': operation.qty_done}, context=context)
                        stock_operation_obj.write(cr, uid, operation.id,
                                                  {'product_qty': operation.product_qty - operation.qty_done,
                                                   'qty_done': 0}, context=context)
                        op = stock_operation_obj.browse(cr, uid, new_operation, context=context)
                    pack_operation_ids.append(op.id)
                    #if op.product_id and op.location_id and op.location_dest_id:
                    #    stock_move_obj.check_tracking_product(cr, uid, op.product_id, op.lot_id.id, op.location_id,
                    #                                          op.location_dest_id, context=context)
                package_id = package_obj.create(cr, uid, {}, context=context)
                stock_operation_obj.write(cr, uid, pack_operation_ids, {'result_package_id': package_id},
                                          context=context)
        return package_id


    class product_ul(models.Model):
        _name = "product.ul"
        _description = "Logistic Unit"
        _columns = {
            'name': osv.fields.char('Name', select=True, required=True, translate=True),
            'type': osv.fields.selection([('unit', 'Unit'), ('pack', 'Pack'), ('box', 'Box'), ('pallet', 'Pallet')], 'Type',
                                     required=True),
            'height': osv.fields.float('Height', help='The height of the package'),
            'width': osv.fields.float('Width', help='The width of the package'),
            'length': osv.fields.float('Length', help='The length of the package'),
            'weight': osv.fields.float('Empty Package Weight'),
        }


    class FluxTenduStocQuantPackage(models.Model):
        _inherit = "stock.quant.package"

        ul_id = fields.Many2one('product.ul', string='Logistic Unit')
