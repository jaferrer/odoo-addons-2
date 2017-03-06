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

from openerp import models, fields, api, exceptions, _
from openerp.tools import float_compare, float_round
from openerp.tools.sql import drop_view_if_exists
from datetime import datetime as dt
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


@job(default_channel='root')
def job_fill_new_picking_for_product(session, model_name, product_id, product_ids, move_tuples, dest_location_id,
                                     picking_type_id, new_picking_id, move_recordset=None, context=None):
    quants_obj = session.env[model_name].with_context(context)
    quants_obj.fill_new_picking_for_product(product_id, product_ids, move_tuples, dest_location_id, picking_type_id,
                                            new_picking_id, move_recordset=move_recordset)
    return "Picking correctly filled"


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def partial_move(self, move_items, product, qty):
        if not move_items.get(product.id):
            move_items[product.id] = []
        move_items[product.id] += [{
            'quant_ids': self.ids,
            'qty': float_round(qty, precision_rounding=product.uom_id.rounding)}]
        return move_items

    @api.model
    def determine_list_reservations(self, product, move_tuples):
        prec = product.uom_id.rounding
        list_reservations = []
        for move_tuple in move_tuples:
            qty_reserved = 0
            qty_to_reserve = move_tuple['qty']
            for quant_id in move_tuple['quant_ids']:
                quant = self.env['stock.quant'].browse(quant_id)
                # If the new quant does not exceed the requested qty, we move it (end of loop) and continue
                # If requested qty is reached, we break the loop
                if float_compare(qty_reserved, qty_to_reserve, precision_rounding=prec) >= 0:
                    break
                # If the new quant exceeds the requested qty, we reserve the good qty and then break
                elif float_compare(qty_reserved + quant.qty, qty_to_reserve, precision_rounding=prec) > 0:
                    list_reservations += [(quant, float_round(qty_to_reserve - qty_reserved, precision_rounding=prec))]
                    break
                list_reservations += [(quant, quant.qty)]
                qty_reserved += quant.qty
        return list_reservations

    @api.model
    def get_corresponding_moves(self, quant, location_from, dest_location, picking_type_id, limit=None,
                                force_domain=None):
        domain = [('product_id', '=', quant.product_id.id),
                  ('state', 'not in', ['draft', 'done', 'cancel']),
                  ('location_id', '=', location_from.id),
                  ('location_dest_id', '=', dest_location.id),
                  ('picking_type_id', '=', picking_type_id)]
        if force_domain:
            domain += force_domain
        moves = self.env['stock.move'].search(domain)
        moves_correct_chain = moves.filtered(lambda move: move in quant.history_ids or
                                                          any([sm in quant.history_ids for sm in move.move_orig_ids]))
        moves_correct_chain = self.env['stock.move'].search([('id', 'in', moves_correct_chain.ids)],
                                                            order='priority desc, date asc, id')
        moves_no_ancestors = moves.filtered(lambda move: move not in quant.history_ids and not move.move_orig_ids)
        moves_no_ancestors = self.env['stock.move'].search([('id', 'in', moves_no_ancestors.ids)],
                                                           order='priority desc, date asc, id')
        return self.env['stock.move'].search([('id', 'in', moves_correct_chain.ids + moves_no_ancestors.ids)],
                                             limit=limit)

    @api.model
    def unreserve_quants_wrong_moves(self, list_reservations, location_from, dest_location, picking_type_id):
        for quant_tuple in list_reservations:
            corresponding_moves = self.get_corresponding_moves(quant_tuple[0], location_from, dest_location,
                                                               picking_type_id)
            if quant_tuple[0].reservation_id and quant_tuple[0].reservation_id not in corresponding_moves:
                quant_tuple[0].reservation_id.do_unreserve()

    @api.model
    def split_and_reserve_moves_ok(self, list_reservations, move_recordset, new_picking):
        processed_moves = move_recordset
        for quant_tuple in list_reservations:
            prec = quant_tuple[0].product_id.uom_id.rounding
            current_reservation = quant_tuple[0].reservation_id
            # We split moves matching requirements using the list of reservations
            if current_reservation and current_reservation not in processed_moves:
                quant_tuples_current_reservation = [tpl for tpl in list_reservations if
                                                    tpl[0].reservation_id == current_reservation]
                # We remove current_reservation from its picking, to prevent from intempestive picking status changes
                old_picking = current_reservation.picking_id
                current_reservation.picking_id = False
                current_reservation.do_unreserve()
                final_qty = sum([tpl[1] for tpl in quant_tuples_current_reservation])
                # Split move if needed
                if float_compare(final_qty, current_reservation.product_qty, precision_rounding=prec) < 0:
                    current_reservation.split(current_reservation,
                                              float_round(current_reservation.product_qty - final_qty,
                                                          precision_rounding=prec))
                # Reserve quants on move
                self.quants_reserve(quant_tuples_current_reservation, current_reservation)
                # Assign the current move to the new picking
                current_reservation.picking_id = new_picking
                if not old_picking.move_lines:
                    old_picking.delete_packops()
                    old_picking.unlink()
                move_recordset |= current_reservation
                processed_moves |= current_reservation
        return move_recordset

    @api.model
    def process_not_reserved_tuples(self, list_reservations, move_recordset, new_picking, location_from,
                                    dest_location, picking_type_id):
        not_reserved_tuples = [item for item in list_reservations if not item[0].reservation_id]
        if not_reserved_tuples:
            done_move_ids = move_recordset.ids
            dict_reservations = {}
            force_domain = [('id', 'not in', done_move_ids)]
            first_corresponding_move = self.get_corresponding_moves(not_reserved_tuples[0][0],
                                                                    location_from, dest_location,
                                                                    picking_type_id, force_domain=force_domain,
                                                                    limit=1)
            while not_reserved_tuples and first_corresponding_move:
                prec = first_corresponding_move.product_id.uom_id.rounding
                if not dict_reservations.get(first_corresponding_move):
                    dict_reservations[first_corresponding_move] = []
                quant = not_reserved_tuples[0][0]
                qty = not_reserved_tuples[0][1]
                # We remove first_corresponding_move from its picking, to prevent from intempestive picking status changes
                old_picking = first_corresponding_move.picking_id
                first_corresponding_move.picking_id = False
                first_corresponding_move.do_unreserve()
                qty_reserved_on_move = sum([tpl[1] for tpl in dict_reservations[first_corresponding_move]])
                # If the current move can exactly assume the new reservation,
                # we reserve the quants and pass to the next one
                if float_compare(qty_reserved_on_move + qty, first_corresponding_move.product_qty,
                                 precision_rounding=prec) == 0:
                    dict_reservations[first_corresponding_move] += [(quant, qty)]
                    done_move_ids += [first_corresponding_move.id]
                # If the current move can assume more than the new reservation,
                # we reserve the quants and stay on this move
                elif float_compare(qty_reserved_on_move + qty, first_corresponding_move.product_qty,
                                   precision_rounding=prec) < 0:
                    dict_reservations[first_corresponding_move] += [(quant, qty)]
                # If the current move can not assume the new reservation, we split the quant
                else:
                    reservable_qty_on_move = first_corresponding_move.product_qty - qty_reserved_on_move
                    splitted_quant = self.env['stock.quant']._quant_split(quant, float_round(reservable_qty_on_move,
                                                                                             precision_rounding=prec))
                    dict_reservations[first_corresponding_move] += [(quant, quant.qty)]
                    not_reserved_tuples += [(splitted_quant, float_round(qty - reservable_qty_on_move,
                                                                         precision_rounding=prec))]
                    done_move_ids += [first_corresponding_move.id]
                first_corresponding_move.picking_id = old_picking
                move_recordset |= first_corresponding_move
                force_domain = [('id', 'not in', done_move_ids)]
                first_corresponding_move = self.get_corresponding_moves(quant, location_from, dest_location,
                                                                        picking_type_id, limit=1,
                                                                        force_domain=force_domain)
                not_reserved_tuples = not_reserved_tuples[1:]
            # Let's split the move which are not entirely_used
            for move in dict_reservations:
                prec = move.product_id.uom_id.rounding
                qty_reserved = sum([tpl[1] for tpl in dict_reservations[move]])
                if float_compare(qty_reserved, move.product_qty, precision_rounding=prec) < 0:
                    move.split(move, float_round(move.product_qty - qty_reserved, precision_rounding=prec))
            # Let's reserve the quants
            for move in dict_reservations:
                old_picking = move.picking_id
                self.quants_reserve(dict_reservations[move], move)
                move.picking_id = new_picking
                if not old_picking.move_lines:
                    old_picking.delete_packops()
                    old_picking.unlink()
        return move_recordset, not_reserved_tuples

    @api.model
    def check_moves_ok(self, list_reservations, location_from, dest_location, picking_type_id, move_recordset,
                       new_picking):
        quants_to_move_in_fine = []
        # First, we unreserve quants which are reserved for a move that does not match requirements
        self.unreserve_quants_wrong_moves(list_reservations, location_from, dest_location, picking_type_id)
        # Now, let's process reservations one by one
        move_recordset = self.split_and_reserve_moves_ok(list_reservations, move_recordset, new_picking)
        # Let's attach unreserved quants to corresponding moves
        move_recordset, not_reserved_tuples = self.process_not_reserved_tuples(list_reservations, move_recordset,
                                                                               new_picking, location_from,
                                                                               dest_location, picking_type_id)
        # For not reserved quants, we will create a new move later
        quants_to_move_in_fine += not_reserved_tuples
        return move_recordset, quants_to_move_in_fine

    @api.model
    def move_remaining_quants(self, product, location_from, dest_location, picking_type_id, new_picking_id,
                              move_recordset, quants_to_move_in_fine):
        if quants_to_move_in_fine:
            new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                'name': 'Move %s to %s' % (product.name, dest_location.name),
                'product_id': product.id,
                'location_id': location_from.id,
                'location_dest_id': dest_location.id,
                'product_uom_qty': float_round(sum([item[1] for item in quants_to_move_in_fine]),
                                               precision_rounding=product.uom_id.rounding),
                'product_uom': product.uom_id.id,
                'date_expected': fields.Datetime.now(),
                'date': fields.Datetime.now(),
                'picking_type_id': picking_type_id,
            })
            new_move.action_confirm()
            self.quants_reserve(quants_to_move_in_fine, new_move)
            new_move.write({'picking_id': new_picking_id})
            move_recordset = move_recordset | new_move
        return move_recordset

    @api.model
    def move_quants_old_school(self, list_reservation, move_recordset, dest_location, picking_type_id, new_picking):
        values = self.env['stock.quant'].read_group([('id', 'in', self.ids)],
                                                    ['product_id', 'location_id', 'qty'],
                                                    ['product_id', 'location_id'], lazy=False)
        for val in values:
            uom = self.env['product.product'].search([('id', '=', val['product_id'][0])]).uom_id
            new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                'name': 'Move %s to %s' % (val['product_id'][1], dest_location.name),
                'product_id': val['product_id'][0],
                'location_id': val['location_id'][0],
                'location_dest_id': dest_location.id,
                'product_uom_qty': float_round(val['qty'], precision_rounding=uom.rounding),
                'product_uom': uom.id,
                'date_expected': fields.Datetime.now(),
                'date': fields.Datetime.now(),
                'picking_type_id': picking_type_id.id,
                'picking_id': new_picking.id,
            })
            quants = self.env['stock.quant'].search([('id', 'in', self.ids),
                                                     ('product_id', '=', val['product_id'][0])])
            qties = quants.read(['id', 'qty'])
            list_reservation[new_move] = []
            for qty in qties:
                list_reservation[new_move].append((self.env['stock.quant'].search(
                    [('id', '=', qty['id'])]), qty['qty']))
            move_recordset = move_recordset | new_move
        return list_reservation, move_recordset

    @api.model
    def fill_new_picking_for_product(self, product_id, product_ids, move_tuples, dest_location_id, picking_type_id,
                                     new_picking_id, move_recordset=None):
        if not move_recordset:
            move_recordset = self.env['stock.move']
        product = self.env['product.product'].browse(product_id)
        first_quant_id = move_tuples[0]['quant_ids'][0]
        location_from = self.env['stock.quant'].browse(first_quant_id).location_id
        dest_location = self.env['stock.location'].browse(dest_location_id)
        new_picking = self.env['stock.picking'].browse(new_picking_id)
        # We determine the needs
        list_reservations = self.determine_list_reservations(product, move_tuples)
        # For not reserved quants, we try to use existing moves
        move_recordset, quants_to_move_in_fine = self.env['stock.quant']. \
            check_moves_ok(list_reservations, location_from, dest_location, picking_type_id,
                           move_recordset, new_picking_id)
        move_recordset = self.move_remaining_quants(product, location_from, dest_location, picking_type_id,
                                                    new_picking_id, move_recordset, quants_to_move_in_fine)
        move_recordset.filtered(lambda move: move.state == 'draft').action_confirm()
        move_recordset.delete_packops()
        done_product_ids = [move.product_id.id for move in new_picking.move_lines]
        if all ([product_id in done_product_ids for product_id in product_ids]):
            new_picking.do_prepare_partial()
            new_picking.picking_correctly_filled = True
        return move_recordset

    @api.multi
    def move_to(self, dest_location, picking_type, move_items=None, is_manual_op=False, filling_method=False):
        """
        :param move_items: {product_id: [{'quant_ids': quants IDs list, 'qty': float}, ...], ...}
        """
        move_recordset = self.env['stock.move']
        list_reservation = {}
        if self:
            new_picking = self.env['stock.picking'].create({'picking_type_id': picking_type.id})
            if move_items:
                index = 0
                product_ids = move_items.keys()
                chunks_number = len(product_ids)
                for product_id in product_ids:
                    product = self.env['product.product'].browse(product_id)
                    move_tuples = move_items[product_id]
                    if not move_tuples:
                        raise exceptions.except_orm(_("error"), _("No move found for product %s") %
                                                    product.display_name)
                    index += 1
                    first_product = index == 1
                    if is_manual_op and filling_method == 'jobify' and not first_product:
                        new_picking.filled_by_jobs = True
                        job_fill_new_picking_for_product.delay(ConnectorSession.from_env(self.env), 'stock.quant',
                                                               product_id, product_ids, move_tuples, dest_location.id,
                                                               picking_type.id, new_picking.id,
                                                               context=self.env.context,
                                                               description=u"Filling picking %s with product %s (%s/%s)" %
                                                                           (new_picking.name, product.display_name,
                                                                            index, chunks_number))
                    else:
                        move_recordset = self.fill_new_picking_for_product(product_id, product_ids, move_tuples,
                                                                           dest_location.id,
                                                                           picking_type.id, new_picking.id,
                                                                           move_recordset=move_recordset)
            else:
                list_reservation, move_recordset = self. \
                    move_quants_old_school(list_reservation, move_recordset, dest_location,
                                           picking_type, new_picking)
                if move_recordset:
                    move_recordset.action_confirm()
                for new_move in list_reservation.keys():
                    if new_move.picking_id != new_picking:
                        raise exceptions.except_orm(_("error"), _("The moves of all the quants could not be "
                                                                  "assigned to the same picking."))
                    self.quants_reserve(list_reservation[new_move], new_move)
            # If the moves have pack operations, we delete it
            new_picking.move_lines.delete_packops()
            new_picking.do_prepare_partial()
            if not is_manual_op:
                # If the transfer is not manual, we do not want the putaway strategies to be applied.
                new_picking.pack_operation_ids.write({'location_dest_id': dest_location.id})
                new_picking.do_transfer()
        return move_recordset


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    filled_by_jobs = fields.Boolean(string="Picking filled by jobs", readonly=True, track_visibility='onchange')
    picking_correctly_filled = fields.Boolean(string="Picking correctly filled", readonly=True,
                                              track_visibility='onchange')


class StockMove(models.Model):
    _inherit = 'stock.move'

    def delete_packops(self):
        for move in self:
            if move.linked_move_operation_ids:
                move.linked_move_operation_ids.unlink()

    @api.multi
    def display_picking_for_moves(self, is_manual_op):
        if is_manual_op:
            if not self:
                raise exceptions.except_orm(_("error"), _("No line selected"))
            return {
                'name': 'picking_form',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': self[0].picking_id.id
            }
        else:
            return self


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    picking_type_id = fields.Many2one('stock.picking.type', string="Default picking type")


class Stock(models.Model):
    _name = 'stock.product.line'
    _auto = False
    _order = 'package_id asc, product_id asc'

    product_id = fields.Many2one('product.product', readonly=True, index=True, string="Product")
    package_id = fields.Many2one("stock.quant.package", string="Package", index=True)
    lot_id = fields.Many2one("stock.production.lot", string="Lot")
    qty = fields.Float(string="Quantity")
    uom_id = fields.Many2one("product.uom", string="UOM")
    location_id = fields.Many2one("stock.location", string="Location")
    parent_id = fields.Many2one("stock.quant.package", "Parent Package", index=True)

    def init(self, cr):
        drop_view_if_exists(cr, 'stock_product_line')
        cr.execute("""CREATE OR REPLACE VIEW stock_product_line AS (
    SELECT
        COALESCE(rqx.product_id, 0)
        || '-' || COALESCE(rqx.package_id, 0) || '-' || COALESCE(rqx.lot_id, 0) || '-' ||
        COALESCE(rqx.uom_id, 0) || '-' || COALESCE(rqx.location_id, 0) AS id,
        rqx.*
    FROM
        (SELECT
             sq.product_id,
             sq.package_id,
             sq.lot_id,
             round(sum(sq.qty) :: NUMERIC, 3) qty,
             pt.uom_id,
             sq.location_id,
             sqp.parent_id
         FROM
             stock_quant sq
             LEFT JOIN product_product pp ON pp.id = sq.product_id
             LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
             LEFT JOIN stock_quant_package sqp ON sqp.id = sq.package_id
         GROUP BY
             sq.product_id,
             sq.package_id,
             sq.lot_id,
             pt.uom_id,
             sq.location_id,
             sqp.parent_id
         UNION ALL
         SELECT
             NULL         product_id,
             sqp.id       package_id,
             NULL         lot_id,
             0 :: NUMERIC qty,
             NULL         uom_id,
             sqp.location_id,
             sqp.parent_id
         FROM
             stock_quant_package sqp
         WHERE exists(SELECT 1
                      FROM
                          stock_quant sq
                          LEFT JOIN stock_quant_package sqp_bis ON sqp_bis.id = sq.package_id
                      WHERE sqp_bis.id = sqp.id
                      GROUP BY sqp_bis.id
                      HAVING count(DISTINCT sq.product_id) <> 1) OR exists(SELECT 1
                                                                           FROM
                                                                               stock_quant_package sqp_bis
                                                                           WHERE sqp_bis.parent_id = sqp.id)
        ) rqx)
            """)

    @api.multi
    def move_products(self):
        if self:
            location = self[0].location_id
            if any([line.location_id != location for line in self]):
                raise exceptions.except_orm(_("error"),
                                            _("Impossible to move simultaneously products of different locations"))
        ctx = self.env.context.copy()
        ctx['active_ids'] = self.ids
        return {
            'name': _("Move products"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.move.wizard',
            'target': 'new',
            'context': ctx,
        }
