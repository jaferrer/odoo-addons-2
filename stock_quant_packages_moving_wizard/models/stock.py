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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import models, fields, api, exceptions, osv, _
from openerp.tools import float_compare, float_round
from openerp.tools.sql import drop_view_if_exists


@job(default_channel='root')
def job_fill_new_picking_for_product(session, model_name, product_id, move_tuples, dest_location_id,
                                     picking_type_id, new_picking_id, context=None):
    quants_obj = session.env[model_name].with_context(context)
    quants_obj.fill_new_picking_for_product(product_id, move_tuples, dest_location_id, picking_type_id,
                                            new_picking_id)
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
            quants = self.env['stock.quant'].search([('id', 'in', move_tuple['quant_ids'])])
            for quant in quants:
                quant_read = quant.read(['id', 'qty'], load=False)[0]
                # If the new quant does not exceed the requested qty, we move it (end of loop) and continue
                # If requested qty is reached, we break the loop
                if float_compare(qty_reserved, qty_to_reserve, precision_rounding=prec) >= 0:
                    break
                # If the new quant exceeds the requested qty, we reserve the good qty and then break
                elif float_compare(qty_reserved + quant_read['qty'], qty_to_reserve, precision_rounding=prec) > 0:
                    list_reservations += [(quant, float_round(qty_to_reserve - qty_reserved, precision_rounding=prec))]
                    break
                list_reservations += [(quant, quant_read['qty'])]
                qty_reserved += quant_read['qty']
        return list_reservations

    @api.model
    def get_corresponding_move_ids(self, quant, location_from, dest_location, picking_type_id, force_domain=None):
        moves_correct_chain_ids = []
        moves_no_ancestors_ids = []
        domain = [('product_id', '=', quant.product_id.id),
                  ('state', 'not in', ['draft', 'done', 'cancel']),
                  ('location_id', '=', location_from.id),
                  ('location_dest_id', '=', dest_location.id),
                  ('picking_type_id', '=', picking_type_id)]
        if force_domain:
            domain += force_domain
        moves = self.env['stock.move'].search(domain)
        move_ids = tuple(moves.ids) or (0,)
        if moves:
            self.env.cr.execute("""WITH correct_moves AS (
    SELECT
        sm.id,
        sm.date,
        sm.priority
    FROM stock_move sm
    WHERE sm.id IN %s)

SELECT sm.id
FROM correct_moves sm
    LEFT JOIN stock_move move_orig ON move_orig.move_dest_id = sm.id
    LEFT JOIN stock_quant_move_rel rel ON rel.quant_id = %s
    LEFT JOIN stock_move move_history ON move_history.id = rel.move_id
WHERE move_orig.id = move_history.id OR
      sm.id = move_history.id
ORDER BY sm.priority DESC, sm.date ASC, sm.id ASC""", (tuple(move_ids), quant.id,))

            moves_correct_chain_ids = [move_id for move_id in set([item[0] for item in self.env.cr.fetchall()])]
            self.env.cr.execute("""WITH nb_ancestors AS (
    SELECT
        sm.id,
        sm.date,
        sm.priority,
        sum(COALESCE(move_orig.id, 0)) AS sum_move_ids
    FROM stock_move sm
        LEFT JOIN stock_move move_orig ON move_orig.move_dest_id = sm.id
    WHERE sm.id IN %s
    GROUP BY sm.id, sm.date, sm.priority)

SELECT sm.id
FROM nb_ancestors sm
WHERE sm.sum_move_ids = 0 AND
      sm.id NOT IN %s
ORDER BY sm.priority DESC, sm.date ASC, sm.id ASC""", (tuple(move_ids), tuple(quant.history_ids.ids or [0]),))
            moves_no_ancestors_ids = [move_id for move_id in set([item[0] for item in self.env.cr.fetchall()])]
        return moves_correct_chain_ids + moves_no_ancestors_ids

    @api.model
    def move_remaining_quants(self, product, location_from, dest_location, picking_type_id, new_picking_id,
                              moves_to_create):
        new_move = self.env['stock.move']
        if moves_to_create:
            new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                'name': 'Move %s to %s' % (product.name, dest_location.name),
                'product_id': product.id,
                'location_id': location_from.id,
                'location_dest_id': dest_location.id,
                'product_uom_qty': float_round(sum([item[1] for item in moves_to_create]),
                                               precision_rounding=product.uom_id.rounding),
                'product_uom': product.uom_id.id,
                'date_expected': fields.Datetime.now(),
                'date': fields.Datetime.now(),
                'picking_type_id': picking_type_id,
                'picking_id': new_picking_id
            })
            new_move.action_confirm()
            self.quants_reserve(moves_to_create, new_move)
        return new_move

    @api.model
    def reserve_quants_on_moves_ok(self, dict_reservation_target):
        for move in dict_reservation_target.keys():
            list_reservations = dict_reservation_target[move]['reservations']
            self.quants_reserve(list_reservations, move)

    @api.model
    def get_reservation_target(self, list_reservations, product, location_from, dest_location, picking_type_id):
        prec = product.uom_id.rounding
        dict_reservation_target = {}
        full_moves = self.env['stock.move']
        moves_to_create = []
        for reservation_tuple in list_reservations:
            quant, target_qty = reservation_tuple
            corresponding_move_ids = self. \
                get_corresponding_move_ids(quant, location_from, dest_location, picking_type_id,
                                           force_domain=[('id', 'not in', full_moves.ids)])
            if quant.reservation_id and quant.reservation_id.id not in corresponding_move_ids:
                quant.reservation_id.do_unreserve()
            for move_id in corresponding_move_ids:
                move = self.env['stock.move'].search([('id', '=', move_id)])
                if move not in dict_reservation_target:
                    dict_reservation_target[move] = {'available_qty': move.product_qty, 'reservations': []}
                    move.do_unreserve()
                if float_compare(target_qty, dict_reservation_target[move]['available_qty'],
                                 precision_rounding=prec) <= 0:
                    dict_reservation_target[move]['reservations'] += [(quant, target_qty)]
                    dict_reservation_target[move]['available_qty'] -= target_qty
                    if float_compare(dict_reservation_target[move]['available_qty'], 0, precision_rounding=prec) <= 0:
                        full_moves |= move
                    target_qty -= move.product_qty
                    break
                else:
                    qty_to_reserve_on_move = dict_reservation_target[move]['available_qty']
                    splitted_quant = quant._quant_split(quant, qty_to_reserve_on_move)
                    dict_reservation_target[move]['reservations'] += [(quant, qty_to_reserve_on_move)]
                    dict_reservation_target[move]['available_qty'] = 0
                    full_moves |= move
                    quant, target_qty = splitted_quant, target_qty - qty_to_reserve_on_move
            if float_compare(target_qty, 0, precision_rounding=prec) > 0:
                moves_to_create += [(quant, target_qty)]
        return dict_reservation_target, moves_to_create

    @api.model
    def fill_new_picking_for_product(self, product_id, move_tuples, dest_location_id, picking_type_id, new_picking_id):
        product = self.env['product.product'].search([('id', '=', product_id)])
        new_picking = self.env['stock.picking'].search([('id', '=', new_picking_id)])
        first_quant_id = move_tuples[0]['quant_ids'][0]
        location_from = self.env['stock.quant'].search([('id', '=', first_quant_id)]).location_id
        dest_location = self.env['stock.location'].search([('id', '=', dest_location_id)])
        # We determine the needs
        list_reservations = self.determine_list_reservations(product, move_tuples)
        dict_reservation_target, moves_to_create = self. \
            get_reservation_target(list_reservations, product, location_from, dest_location, picking_type_id)
        self.env['stock.move'].split_not_totally_consumed_moves(dict_reservation_target)
        self.reserve_quants_on_moves_ok(dict_reservation_target)
        new_moves = self.move_remaining_quants(product, location_from, dest_location, picking_type_id,
                                               new_picking_id, moves_to_create)
        new_moves.assign_moves_to_new_picking(dict_reservation_target, new_picking_id)
        moves_to_confirm = self.env['stock.move'].search([('picking_id', '=', new_picking_id),
                                                          ('state', '=', 'draft')])
        if moves_to_confirm:
            moves_to_confirm.action_confirm()
        new_picking.move_lines.delete_packops()
        products_filled = self.env['product.to.be.filled'].search([('picking_id', '=', new_picking_id),
                                                                   ('product_id', '=', product_id)])
        if products_filled:
            products_filled.write({'filled': True,
                                   'filled_at': fields.Datetime.now()})

    @api.multi
    def get_default_move_items(self):
        move_items = {}
        for quant in self:
            if quant.product_id.id not in move_items:
                move_items[quant.product_id.id] = []
            move_items[quant.product_id.id] += [{'quant_ids': quant.ids, 'qty': quant.qty}]
        return move_items

    @api.multi
    def move_to(self, dest_location, picking_type, move_items=None, is_manual_op=False, filling_method=False):
        """
        :param move_items: {product_id: [{'quant_ids': quants IDs list, 'qty': float}, ...], ...}
        """
        if not self:
            return self.env['stock.picking']
        if not move_items:
            move_items = self.get_default_move_items()
        new_picking = self.env['stock.picking'].create({'picking_type_id': picking_type.id})
        index = 0
        product_ids = move_items.keys()
        product_ids = sorted(product_ids, key=lambda product_id: sum(
            [dict_reservation['qty'] for dict_reservation in move_items[product_id]]))
        chunks_number = len(product_ids)
        first_product = True
        for product_id in product_ids:
            if is_manual_op and filling_method == 'jobify' and first_product:
                new_picking.filled_by_jobs = True
            self.env['product.to.be.filled'].create({'picking_id': new_picking.id,
                                                     'product_id': product_id})
            product = self.env['product.product'].browse(product_id)
            move_tuples = move_items[product_id]
            if not move_tuples:
                raise exceptions.except_orm(_("error"), _("No move found for product %s") %
                                            product.display_name)
            index += 1
            if is_manual_op and filling_method == 'jobify' and not first_product:
                description = u"Filling picking %s with product %s (%s/%s)" % \
                              (new_picking.name, product.display_name, index, chunks_number)
                job_fill_new_picking_for_product.delay(ConnectorSession.from_env(self.env), 'stock.quant',
                                                       product_id, move_tuples, dest_location.id,
                                                       picking_type.id, new_picking.id,
                                                       context=dict(self.env.context),
                                                       description=description)
            else:
                self.fill_new_picking_for_product(product_id, move_tuples,
                                                  dest_location.id,
                                                  picking_type.id, new_picking.id)
            first_product = False
        new_picking.move_lines.delete_packops()
        new_picking.do_prepare_partial()
        if not is_manual_op:
            # If the transfer is not manual, we do not want the putaway strategies to be applied.
            new_picking.pack_operation_ids.write({'location_dest_id': dest_location.id})
            new_picking.do_transfer()
        return new_picking

    @api.multi
    def get_natural_loc_picking_type(self):
        natural_dest_loc = False
        natural_picking_type = False
        list_next_moves = self.env['stock.move']
        for rec in self:
            service_moves = self.env['stock.move']. \
                search([('id', 'in', rec.history_ids.ids),
                        ('state', '=', 'done'),
                        ('location_dest_id', '=', rec.location_id.id),
                        ('move_dest_id', '!=', False),
                        ('move_dest_id.state', 'not in', [('draft', 'done', 'cancel')])])
            for service_move in service_moves:
                list_next_moves  |= service_move.move_dest_id
        list_dest_locs = [move.location_dest_id for move in list_next_moves]
        list_picking_types = [move.picking_type_id for move in list_next_moves]
        if len(set(list_dest_locs)) == 1:
            natural_dest_loc = list_dest_locs[0]
        if len(set(list_picking_types)) == 1:
            natural_picking_type = list_picking_types[0]
        return natural_dest_loc, natural_picking_type


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.cr_uid_ids_context
    def _compute_group_id(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            new_group = picking.move_lines and picking.move_lines[0].group_id or picking.group_id
            if new_group == picking.group_id:
                continue
            res[picking.id] = new_group and new_group.id or False
        return res

    @api.cr_uid_ids_context
    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    filled_by_jobs = fields.Boolean(string="Picking filled by jobs", readonly=True, track_visibility='onchange')
    picking_correctly_filled = fields.Boolean(string="Picking correctly filled", readonly=True,
                                              track_visibility='onchange')
    product_to_be_filled_ids = fields.One2many('product.to.be.filled', 'picking_id',
                                               string=u"Products to fill")

    _columns = {
        'group_id': osv.fields.function(
            _compute_group_id, type='many2one', relation='procurement.group',
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_lines'], 20),
                'stock.move': (_get_pickings, ['group_id', 'picking_id'], 20)}
        ),
    }

    @api.model
    def check_pickings_filled(self):
        pickings_to_check = self.env['stock.picking'].search([('filled_by_jobs', '=', True),
                                                              ('picking_correctly_filled', '=', False),
                                                              ('state', 'not in', [('done', 'cancel')])])
        for picking in pickings_to_check:
            products_not_filled = self.env['product.to.be.filled'].search([('picking_id', '=', picking.id),
                                                                           ('filled', '=', False)])
            if not products_not_filled:
                picking.do_prepare_partial()
                picking.picking_correctly_filled = True

    @api.multi
    def open_picking_form(self, is_manual_op):
        if is_manual_op:
            if not self:
                raise exceptions.except_orm(_("error"), _("No line selected"))
            return {
                'name': 'picking_form',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': self.id
            }
        else:
            return self


class StockMove(models.Model):
    _inherit = 'stock.move'

    def delete_packops(self):
        for move in self:
            if move.linked_move_operation_ids:
                move.linked_move_operation_ids.unlink()

    @api.model
    def split_not_totally_consumed_moves(self, dict_reservation_target):
        for move in dict_reservation_target.keys():
            prec = move.product_id.uom_id.rounding
            required_qty = sum([quant_tuple[1] for quant_tuple in dict_reservation_target[move]['reservations']])
            if float_compare(move.product_qty, required_qty, precision_rounding=prec) > 0:
                move.split(move, float_round(move.product_qty - required_qty, precision_rounding=prec))

    @api.multi
    def assign_moves_to_new_picking(self, dict_reservation_target, new_picking_id):
        moves = self.search([('id', 'in', self.ids + [move.id for move in dict_reservation_target.keys()])])
        if moves:
            pickings = set([move.picking_id for move in moves])
            moves.write({'picking_id': new_picking_id})
            for picking in pickings:
                if not picking.move_lines:
                    picking.delete_packops()
                    picking.sudo().unlink()


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    picking_type_id = fields.Many2one('stock.picking.type', string="Default picking type")


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    force_is_manual_op = fields.Boolean(string=u"Force manual moves")


class Stock(models.Model):
    _name = 'stock.product.line'
    _auto = False
    _order = 'package_name asc, product_name asc'

    product_id = fields.Many2one('product.product', readonly=True, index=True, string="Product")
    product_name = fields.Char(string="Product name")
    package_id = fields.Many2one("stock.quant.package", string="Package", index=True)
    package_name = fields.Char(string="Package name")
    lot_id = fields.Many2one("stock.production.lot", string="Lot")
    qty = fields.Float(string="Quantity")
    uom_id = fields.Many2one("product.uom", string="UOM")
    location_id = fields.Many2one("stock.location", string="Location")
    parent_id = fields.Many2one("stock.quant.package", "Parent Package", index=True)
    is_package = fields.Boolean(string="Is a package", readonly=True)

    def init(self, cr):
        drop_view_if_exists(cr, 'stock_product_line')
        cr.execute("""CREATE OR REPLACE VIEW stock_product_line AS (
    WITH nb_products_by_package AS (
        SELECT
            sqp.id                        AS package_id,
            count(DISTINCT sq.product_id) AS nb_products
        FROM
            stock_quant sq
            LEFT JOIN stock_quant_package sqp ON sqp.id = sq.package_id
        GROUP BY sqp.id)

    SELECT
        COALESCE(rqx.product_id, 0)
        || '-' || COALESCE(rqx.package_id, 0) || '-' || COALESCE(rqx.lot_id, 0) || '-' ||
        COALESCE(rqx.uom_id, 0) || '-' || COALESCE(rqx.location_id, 0) AS id,
        rqx.*,
        (CASE WHEN rqx.product_id IS NULL OR nb_products.nb_products <= 1
            THEN TRUE
         ELSE FALSE END)                                               AS is_package
    FROM
        (SELECT
             sq.product_id,
             pp.name_template AS              product_name,
             sq.package_id,
             sqp.name         AS              package_name,
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
             LEFT JOIN nb_products_by_package nb_products ON nb_products.package_id = sqp.id
         GROUP BY
             sq.product_id,
             pp.name_template,
             sq.package_id,
             sqp.name,
             sq.lot_id,
             pt.uom_id,
             sq.location_id,
             sqp.parent_id
         UNION ALL
         SELECT
             NULL         product_id,
             NULL     AS  product_name,
             sqp.id       package_id,
             sqp.name AS  package_name,
             NULL         lot_id,
             0 :: NUMERIC qty,
             NULL         uom_id,
             sqp.location_id,
             sqp.parent_id
         FROM
             stock_quant_package sqp
             LEFT JOIN nb_products_by_package nb_products ON nb_products.package_id = sqp.id
         WHERE nb_products.nb_products != 1 OR
               exists(SELECT 1
                      FROM
                          stock_quant_package sqp_bis
                      WHERE sqp_bis.parent_id = sqp.id)
        ) rqx
        LEFT JOIN nb_products_by_package nb_products ON nb_products.package_id = rqx.package_id)
            """)

    @api.model
    def get_default_lines_data_for_wizard(self):
        quant_lines = []
        package_lines = []
        for line in self:
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
                quant_lines.append(line_dict)
            else:
                package_lines.append(line_dict)
        return quant_lines, package_lines

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


class ProductToBeFilled(models.Model):
    _name = 'product.to.be.filled'

    picking_id = fields.Many2one('stock.picking', string=u"Stock Picking")
    product_id = fields.Many2one('product.product', string=u"Product")
    filled = fields.Boolean(string=u"Filled")
    filled_at = fields.Datetime(string=u"Filled at")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.multi
    def get_default_loc_picking_type(self, product):
        self.ensure_one()
        if product:
            product.ensure_one()
        pull_rule = False
        push_rule = False
        if product:
            pull_rule = self.env['procurement.rule'].search([('location_src_id', '=', self.id),
                                                             ('route_id.product_selectable', '=', True),
                                                             ('route_id', 'in', product.route_ids.ids)],
                                                            limit=1)
            push_rule = self.env['stock.location.path'].search([('location_from_id', '=', self.id),
                                                                ('route_id.product_selectable', '=', True),
                                                                ('route_id', 'in', product.route_ids.ids)],
                                                               limit=1)
            if not pull_rule and not push_rule and product.categ_id:
                pull_rule = self.env['procurement.rule'].search([('location_src_id', '=', self.id),
                                                                 ('route_id.product_categ_selectable', '=', True),
                                                                 ('route_id', 'in', product.categ_id.route_ids.ids)],
                                                                limit=1)
                push_rule = self.env['stock.location.path'].search([('location_from_id', '=', self.id),
                                                                    ('route_id.product_categ_selectable', '=', True),
                                                                    ('route_id', 'in', product.categ_id.route_ids.ids)],
                                                                   limit=1)
        if not pull_rule and not push_rule and self:
            warehouse_id = self.get_warehouse(location=self)
            if warehouse_id:
                warehouse = self.env['stock.warehouse'].search([('id', '=', warehouse_id)])
                pull_rule = self.env['procurement.rule'].search([('location_src_id', '=', self.id),
                                                                 ('route_id.warehouse_selectable', '=', True),
                                                                 ('route_id', 'in', warehouse.route_ids.ids)],
                                                                limit=1)
                push_rule = self.env['stock.location.path'].search([('location_from_id', '=', self.id),
                                                                    ('route_id.warehouse_selectable', '=', True),
                                                                    ('route_id', 'in', warehouse.route_ids.ids)],
                                                                   limit=1)
        if pull_rule:
            return pull_rule.location_id, pull_rule.picking_type_id
        elif push_rule:
            return push_rule.location_dest_id, push_rule.picking_type_id
        else:
            return False, False
