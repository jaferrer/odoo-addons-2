# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.tools import drop_view_if_exists, flatten, float_compare, float_round
from openerp import fields, models, api, osv, _
from openerp.osv import fields as old_api_fields
from openerp.addons.procurement import procurement
from openerp.addons.scheduler_async import scheduler_async
from openerp.addons.connector.session import ConnectorSession

assign_moves = scheduler_async.assign_moves

PRODUCT_CHUNK = 1

SQL_REQUEST_BY_MOVE = """
WITH
    RECURSIVE top_parent(loc_id, top_parent_id) AS (
        SELECT
            sl.id AS loc_id,
            sl.id AS top_parent_id
        FROM
            stock_location sl
            LEFT JOIN stock_location slp ON sl.location_id = slp.id
        WHERE
            sl.usage = 'internal'
        UNION
        SELECT
            sl.id AS loc_id,
            tp.top_parent_id
        FROM
            stock_location sl, top_parent tp
        WHERE
            sl.usage = 'internal' AND sl.location_id = tp.loc_id
    ),

    move_qties_interm AS (
        SELECT
            sm.id              AS move_id,
            sm.picking_id,
            sm.location_id,
            sm.product_id,
            sum(sm.product_qty)
            OVER (
                PARTITION BY sm.product_id, sm.picking_id, sm.location_id
                ORDER BY sm.priority DESC, sm.date_expected, sm.id
            ) - sm.product_qty AS qty
        FROM stock_move sm
            INNER JOIN (SELECT
                            sm.picking_id,
                            sm.location_id,
                            sm.product_id
                        FROM stock_move sm
                        WHERE sm.id IN %s
                        GROUP BY sm.picking_id,
                            sm.location_id,
                            sm.product_id) sms
                ON COALESCE(sms.picking_id, -1) = COALESCE(sm.picking_id, -1) AND sm.location_id = sms.location_id AND
                   sm.product_id = sms.product_id
        WHERE sm.picking_type_id IS NOT NULL AND sm.state = 'confirmed' AND NOT EXISTS(
            SELECT 1
            FROM stock_quant sq
            WHERE sq.reservation_id = sm.id
        )
    ),

    not_reserved_quantities AS (
        SELECT
            tp.top_parent_id AS location_id,
            sq.product_id,
            sum(sq.qty)      AS qty
        FROM stock_quant sq
            LEFT JOIN top_parent tp ON tp.loc_id = sq.location_id
        WHERE sq.reservation_id IS NULL
        GROUP BY tp.top_parent_id, sq.product_id
    )

SELECT DISTINCT
    sm.id         AS move_id
FROM
    stock_move sm
    LEFT JOIN stock_move smp ON smp.move_dest_id = sm.id
    LEFT JOIN stock_move sms ON sm.split_from = sms.id
    LEFT JOIN stock_move smps ON smps.move_dest_id = sms.id
WHERE
    sm.state = 'waiting'
    AND sm.picking_type_id IS NOT NULL
    AND (smp.state = 'done' OR smps.state = 'done')
    AND sm.id IN %s
UNION ALL
SELECT
    mqi.move_id
FROM
    move_qties_interm mqi
    LEFT JOIN
    not_reserved_quantities nrq ON nrq.product_id = mqi.product_id AND nrq.location_id = mqi.location_id
WHERE mqi.qty <= nrq.qty AND mqi.move_id IN %s"""

SQL_REQUEST_NO_PICKING = """
WITH RECURSIVE
        top_parent(loc_id, top_parent_id) AS (
        SELECT
            sl.id AS loc_id,
            sl.id AS top_parent_id
        FROM
            stock_location sl
            LEFT JOIN stock_location slp ON sl.location_id = slp.id
        WHERE
            sl.usage = 'internal'
        UNION
        SELECT
            sl.id AS loc_id,
            tp.top_parent_id
        FROM
            stock_location sl, top_parent tp
        WHERE
            sl.usage = 'internal' AND sl.location_id = tp.loc_id
    ),

        confirmed_moves_with_picking_type AS (
        SELECT
            id,
            state,
            picking_id,
            location_id,
            location_dest_id,
            product_id,
            product_qty,
            priority,
            date_expected
        FROM stock_move
        WHERE picking_type_id IS NOT NULL
              AND state = 'confirmed'
              AND defer_picking_assign = TRUE
    ),

        reserved_quants AS (
        SELECT
            DISTINCT sq.reservation_id
        FROM stock_quant sq
        WHERE sq.reservation_id IS NOT NULL
    ),

        moves_with_quants_reserved AS (
        SELECT
            sm.id,
            sm.picking_type_id,
            sm.picking_id
        FROM stock_move sm
            INNER JOIN reserved_quants sq ON sq.reservation_id = sm.id
        WHERE sm.picking_id IS NULL
              AND sm.picking_type_id IS NOT NULL
    ),

        move_qties_interm AS (
        SELECT
            sm.id              AS move_id,
            sm.picking_id,
            sm.location_id,
            sm.product_id,
            sum(sm.product_qty)
            OVER (
                PARTITION BY sm.product_id, sm.location_id, sm.location_dest_id
                ORDER BY sm.priority DESC, sm.date_expected, sm.id
            ) - sm.product_qty AS qty
        FROM confirmed_moves_with_picking_type sm
        WHERE NOT exists(
            SELECT 1
            FROM stock_quant sq
            WHERE sq.reservation_id = sm.id
        )
    ),

        ordered_quants AS (
        SELECT
            sq.product_id,
            sq.qty,
            sq.location_id,
            sq.reservation_id
        FROM stock_quant sq
        WHERE sq.reservation_id IS NULL
        ORDER BY product_id
    ),

        not_reserved_quantities AS (
        SELECT
            tp.top_parent_id AS location_id,
            sq.product_id,
            sum(sq.qty)      AS qty
        FROM ordered_quants sq
            INNER JOIN top_parent tp ON tp.loc_id = sq.location_id
        WHERE tp.top_parent_id IN (SELECT DISTINCT location_id
                                   FROM move_qties_interm)
        GROUP BY sq.product_id, tp.top_parent_id
    ),

        move_qties AS (
        SELECT
            mqi.*,
            nrq.qty        AS sum_qty,
            CASE WHEN mqi.qty <= nrq.qty
                THEN TRUE
            ELSE FALSE END AS flag
        FROM move_qties_interm mqi
            INNER JOIN not_reserved_quantities nrq ON nrq.product_id = mqi.product_id
                                                      AND nrq.location_id = mqi.location_id
        WHERE mqi.picking_id IS NULL
    )

SELECT
    foo.move_id AS id,
    foo.move_id,
    foo.picking_id,
    foo.reserved
FROM (
         SELECT
             sm.id         AS move_id,
             sm.picking_id AS picking_id,
             TRUE          AS reserved
         FROM
             moves_with_quants_reserved sm

         UNION ALL
         SELECT DISTINCT
             sm.id         AS move_id,
             sm.picking_id AS picking_id,
             FALSE         AS reserved
         FROM
             stock_move sm
             LEFT JOIN stock_move smp ON smp.move_dest_id = sm.id AND smp.state = 'done'
             LEFT JOIN stock_move sms ON sm.split_from = sms.id
             LEFT JOIN stock_move smps ON smps.move_dest_id = sms.id AND smps.state = 'done'
         WHERE
             sm.state = 'waiting'
             AND sm.picking_type_id IS NOT NULL
             AND sm.picking_id IS NULL
             AND (smp.state = 'done' OR smps.state = 'done')
         UNION ALL
         SELECT
             mq.move_id,
             mq.picking_id,
             FALSE AS reserved
         FROM move_qties mq
         WHERE flag = TRUE
         UNION ALL
         SELECT
             sm.id         AS move_id,
             sm.picking_id AS picking_id,
             FALSE         AS reserved
         FROM stock_move sm
         WHERE sm.state = 'confirmed'
               AND sm.picking_type_id IS NOT NULL
               AND sm.picking_id IS NULL
               AND sm.defer_picking_assign = FALSE
     ) foo"""


class StockQuantPackageImproved(models.Model):
    _inherit = "stock.quant.package"

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the package must be unique!')
    ]

    def _get_all_products_quantities(self, cr, uid, package_id, context=None):
        '''This function computes the different product quantities for the given package
        '''
        quant_obj = self.pool.get('stock.quant')
        res = {}
        ids = self.get_content(cr, uid, package_id, context=context)
        for quant in quant_obj.read(cr, uid, ids,
                                    ["product_id", "qty"], load=False, context=context):
            if quant["product_id"] not in res:
                res[quant["product_id"]] = 0
            res[quant["product_id"]] += quant["qty"]
        return res

    @api.multi
    def open_bulk_content(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['search_default_productgroup'] = True
        return {
            'name': _("Bulk content for package %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'stock.quant',
            'domain': [('package_id', '=', self.id)],
            'context': ctx,
        }


class stock_pack_operation(models.Model):
    _inherit = "stock.pack.operation"

    def _get_remaining_prod_quantities(self, cr, uid, operation, context=None):
        '''Get the remaining quantities per product on an operation with a package. This function returns a dictionary'''
        # if the operation doesn't concern a package, it's not relevant to call this function
        if not operation.package_id or operation.product_id:
            return {operation.product_id.id: operation.remaining_qty}
        # get the total of products the package contains
        res = self.pool.get('stock.quant.package')._get_all_products_quantities(cr, uid, operation.package_id.id,
                                                                                context=context)
        list_ids = operation.linked_move_operation_ids.ids
        if list_ids:
            cr.execute("""
            SELECT
                sm.product_id,
                sum(smol.qty) qty
            FROM stock_move_operation_link smol
            INNER JOIN stock_move sm ON sm.id=smol.move_id
            WHERE smol.id IN %s
            GROUP BY sm.product_id
            """, (tuple(list_ids),))
            list_linked_move_operations = cr.fetchall()
            # reduce by the quantities linked to a move
            for record in list_linked_move_operations:
                if record[0] not in res:
                    res[record[0]] = 0
                res[record[0]] -= record[1]

        if context.get("test_transfer"):
            test = super(stock_pack_operation, self)._get_remaining_prod_quantities(cr, uid, operation,
                                                                                    context=context)
            if len(test) == len(res):

                for item in test.keys():
                    if float_compare(test[item], res[item],
                                     precision_rounding=self.pool.get('product.product').browse(cr, uid, [item],
                                                                                                context)[
                                         0].uom_id.rounding) != 0:
                        raise osv.except_osv(_('test non regression!'), "_get_remaining_prod_quantities")
            else:
                raise osv.except_osv(_('test non regression!'), "les resulta n'ont pas la meme longueur")
        return res

    @api.multi
    def get_list_operations_to_process(self):
        return [self]

    @api.multi
    def sort_operations_for_transfer(self):
        return sorted(self, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) +
                                          (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_id = fields.Many2one("stock.location", string="Location", readonly=True, compute="_compute_location_id")
    location_dest_id = fields.Many2one("stock.location", string="Destination Location", readonly=True,
                                       compute="_compute_location_id")

    @api.depends('move_lines.location_id', 'move_lines.location_dest_id')
    def _compute_location_id(self):
        for rec in self:
            moves = self.env['stock.move'].search([('picking_id', '=', rec.id)], limit=1)
            if moves:
                rec.location_id = moves.location_id
                rec.location_dest_id = moves.location_dest_id

    @api.model
    def assign_moves_to_picking(self):
        """Assign prereserved moves that do not belong to a picking yet to a picking.
        """
        self.env.cr.execute(SQL_REQUEST_NO_PICKING)
        prereservations = self.env.cr.fetchall()
        prereserved_move_ids = [p[0] for p in prereservations]
        todo_moves = self.env['stock.move'].search([('id', 'in', prereserved_move_ids)])
        todo_moves.assign_to_picking()

    @api.model
    def process_prereservations(self):
        """Remove picking_id from confirmed moves (i.e. not assigned) that should be defered and that are bound to a
        picking. Then call assign_moves_to_picking to get everything back in place.
        """
        todo_moves = self.env['stock.move'].search(
            [('picking_id', '!=', False), ('defer_picking_assign', '=', True), ('state', '=', 'confirmed'),
             ('partially_available', '=', False)]
        )
        todo_moves.with_context(mail_notrack=True).write({'picking_id': False})
        links = self.env['stock.move.operation.link'].search([('move_id', 'in', todo_moves.ids)])
        links.unlink()
        self.assign_moves_to_picking()

    @api.multi
    def action_assign(self):
        """Check availability of picking moves.

        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to assign prereserved moves to pickings beforehand.
        :return: True
        """
        self.with_context(only_pickings=self.ids).assign_moves_to_picking()
        return super(StockPicking, self).action_assign()

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to assign prereserved moves to pickings beforehand
        """
        self.with_context(only_pickings=self.ids).assign_moves_to_picking()
        super(StockPicking, self).rereserve_pick()

    @api.model
    def rereserve_quants(self, picking, move_ids=[]):
        """Speed up quant rereservation by not tracking modifications."""
        super(StockPicking, self.with_context(mail_notrack=True)).rereserve_quants(picking, move_ids)

    @api.cr_uid_ids_context
    def get_min_max_date(self, cr, uid, ids, field_name, arg, context=None):
        """ Finds minimum and maximum dates for picking.
        @return: Dictionary of values
        """
        res = super(StockPicking, self).get_min_max_date(cr, uid, ids, field_name, arg, context=context)
        for k, v in res.iteritems():
            move_ids = self.pool.get('stock.move').search(cr, uid, [('picking_id', '=', k)], limit=1, context=context)
            if move_ids:
                defer = \
                    self.pool.get('stock.move').read(cr, uid, move_ids, ['defer_picking_assign'], context=context)[0][
                        'defer_picking_assign']
                if defer:
                    res[k] = {}
        return res

    def process_operations_for_transfer(self, cr, uid, operations, need_rereserve, still_to_do, prod2move_ids,
                                        quants_in_package_done, context=None):
        uom_obj = self.pool.get('product.uom')
        package_obj = self.pool.get('stock.quant.package')
        picking_obj = self.pool.get('stock.picking')
        quant_obj = self.pool.get('stock.quant')
        operations = operations.sort_operations_for_transfer()
        for ops in operations:
            # for each operation, create the links with the stock move by seeking on the matching reserved quants,
            # and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id:
                # entire package
                quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
                for quant in quant_obj.read(cr, uid, quant_ids,
                                            ['id', 'qty', 'product_id', 'package_id', 'lot_id', 'owner_id',
                                             'reservation_id'], load=False, context=context):
                    remaining_qty_on_quant = quant["qty"]
                    if quant["reservation_id"]:
                        # avoid quants being counted twice
                        quants_in_package_done.add(quant["id"])
                        qty_on_link, prod2move_ids = picking_obj. \
                            _create_link_for_quant(cr, uid, prod2move_ids, ops.id, quant, quant["qty"], context=context)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant["product_id"], remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                # Check moves with same product
                qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty,
                                                         ops.product_id.uom_id, context=context)
                for move_dict in prod2move_ids.get(ops.product_id.id, [])[:]:
                    move = move_dict['move']
                    qts = quant_obj.search(cr, uid, [('reservation_id', '=', move["id"])], context=context)
                    for quant in quant_obj.read(cr, uid, qts,
                                                ['id', 'qty', 'product_id', 'package_id', 'lot_id', 'owner_id',
                                                 'reservation_id'], load=False, context=context):
                        if not qty_to_assign > 0:
                            break
                        if quant["id"] in quants_in_package_done:
                            continue

                        # check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant["package_id"] and bool(
                                package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])],
                                                   context=context)) or False
                        else:
                            flag = not quant["package_id"]
                        flag = flag and ((ops.lot_id and ops.lot_id.id == quant["lot_id"]) or not ops.lot_id)
                        flag = flag and (ops.owner_id.id == quant["owner_id"])
                        if flag:
                            max_qty_on_link = min(quant["qty"], qty_to_assign)
                            qty_on_link, prod2move_ids = picking_obj. \
                                _create_link_for_quant(cr, uid, prod2move_ids, ops.id, quant, max_qty_on_link,
                                                       context=context)
                            qty_to_assign -= qty_on_link
                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    # qty reserved is less than qty put in operations. We need to create a link but it's deferred
                    # after we processed all the quants (because they leave no choice on their related move and needs
                    # to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True
        return still_to_do, need_rereserve, prod2move_ids, quants_in_package_done

    @api.model
    def _create_link_for_index(self, prod2move_ids, operation_id, index, product_id, qty_to_assign, quant_id=False):
        move_dict = prod2move_ids[product_id][index]
        qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
        self.env['stock.move.operation.link'].create({'move_id': move_dict['move']["id"],
                                                      'operation_id': operation_id,
                                                      'qty': qty_on_link,
                                                      'reserved_quant_id': quant_id})
        rounding = self.env['product.product'].browse(product_id).uom_id.rounding
        if float_compare(move_dict['remaining_qty'], qty_on_link, precision_rounding=rounding) == 0:
            prod2move_ids[product_id].pop(index)
        else:
            move_dict['remaining_qty'] -= qty_on_link
        return qty_on_link, prod2move_ids

    @api.model
    def _create_link_for_quant(self, prod2move_ids, operation_id, quant, qty):
        """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
        if not quant["reservation_id"]:
            return self._create_link_for_product(prod2move_ids, operation_id, quant["product_id"], qty)[0]
        qty_on_link = 0
        for i in range(0, len(prod2move_ids[quant["product_id"]])):
            if prod2move_ids[quant["product_id"]][i]['move']['id'] != quant["reservation_id"]:
                continue
            qty_on_link, prod2move_ids = self._create_link_for_index(prod2move_ids, operation_id, i,
                                                                     quant["product_id"], qty, quant_id=quant["id"])
            break
        return qty_on_link, prod2move_ids

    @api.model
    def _create_link_for_product(self, prod2move_ids, operation_id, product_id, qty):
        '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
        Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
        qty_to_assign = qty
        product = self.env['product.product'].browse([product_id])
        rounding = product.uom_id.rounding
        qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
        if prod2move_ids.get(product_id):
            while prod2move_ids[product_id] and qtyassign_cmp > 0:
                qty_on_link, prod2move_ids = self._create_link_for_index(prod2move_ids, operation_id, 0, product_id,
                                                                         qty_to_assign, quant_id=False)
                qty_to_assign -= qty_on_link
                qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
        result_comp = qtyassign_cmp == 0
        return result_comp, prod2move_ids

    @api.model
    def _create_prod2move_ids(self, picking_id):
        prod2move_ids = {}
        self.env.cr.execute(
            """
SELECT
  id,
  product_qty,
  product_id,
  (CASE WHEN sm.state = 'assigned'
    THEN -2
   ELSE 0 END) + (CASE WHEN sm.partially_available
    THEN -1
                  ELSE 0 END) AS poids
FROM stock_move sm
WHERE sm.picking_id = %s AND sm.state NOT IN ('done', 'cancel')
ORDER BY poids ASC,""" + self.pool.get('stock.move')._order + """
                    """, (picking_id,)
        )
        res = self.env.cr.fetchall()
        for move in res:
            if not prod2move_ids.get(move[2]):
                prod2move_ids[move[2]] = [{'move': {'id': move[0]}, 'remaining_qty': move[1]}]
            else:
                prod2move_ids[move[2]].append({'move': {'id': move[0]}, 'remaining_qty': move[1]})
        return prod2move_ids

    def recompute_remaining_qty(self, cr, uid, picking, context=None):
        picking_obj = self.pool.get('stock.picking')
        link_obj = self.pool.get('stock.move.operation.link')
        still_to_do = []
        # make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        # moves_ids = sorted([x for x in picking.move_lines if x.state not in ('done', 'cancel')],
        #               key=lambda x: (((x.state == 'assigned') and -2 or 0) + (x.partially_available and -1 or 0)))

        prod2move_ids = self._create_prod2move_ids(cr, uid, picking.id, context=context)

        if context.get("test_transfer"):
            prod2move_ids_test = {}
            moves_test = sorted([x for x in picking.move_lines if x.state not in ('done', 'cancel')],
                                key=lambda x: (
                                    ((x.state == 'assigned') and -2 or 0) + (x.partially_available and -1 or 0)))
            for move_test in moves_test:
                if not prod2move_ids_test.get(move_test.product_id.id):
                    prod2move_ids_test[move_test.product_id.id] = [
                        {'move': move_test, 'remaining_qty': move_test.product_qty}]
                else:
                    prod2move_ids_test[move_test.product_id.id].append(
                        {'move': move_test, 'remaining_qty': move_test.product_qty})

            if len(prod2move_ids) == len(prod2move_ids_test):
                for it in prod2move_ids_test.keys():
                    if prod2move_ids[it] and len(prod2move_ids[it]) == len(prod2move_ids_test[it]):
                        for a, b in enumerate(prod2move_ids_test[it]):
                            if prod2move_ids[it][a]['move']['id'] != prod2move_ids_test[it][a]['move'].id:
                                raise osv.except_osv(_('test temps do_transfer!'), "recompute_remaining_qty")

                            if float_compare(prod2move_ids[it][a]['remaining_qty'],
                                             prod2move_ids_test[it][a]['remaining_qty'],
                                             precision_rounding=self.pool.get('stock.move').browse(cr, uid, [
                                                 prod2move_ids[it][a]['move']['id']],
                                context)[
                                                 0].product_id.uom_id.rounding) != 0:
                                raise osv.except_osv(_('test temps do_transfer!'), "recompute_remaining_qty")

                    else:
                        raise osv.except_osv(_('test temps do_transfer!'), "recompute_remaining_qty")
            else:
                raise osv.except_osv(_('test temps do_transfer!'), "recompute_remaining_qty")

        need_rereserve = False
        # sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        list_operations_to_process = operations.get_list_operations_to_process()
        operations = operations.sort_operations_for_transfer()
        # delete existing operations to start again from scratch
        links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
        if links:
            link_obj.unlink(cr, uid, links, context=context)
        # 1) first, try to create links when quants can be identified without any doubt
        quants_in_package_done = set()
        for list_operation in list_operations_to_process:
            still_to_do, need_rereserve, prod2move_ids, quants_in_package_done = self.pool.get('stock.picking'). \
                process_operations_for_transfer(cr, uid, list_operation, need_rereserve, still_to_do, prod2move_ids,
                                                quants_in_package_done, context=context)

        # 2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            result_comp, prod2move_ids = picking_obj. \
                _create_link_for_product(cr, uid, prod2move_ids, ops.id, product_id, remaining_qty, context=context)
            all_op_processed = all_op_processed and result_comp

        if context.get("test_transfer"):
            test = super(StockPicking, self).recompute_remaining_qty(cr, uid, picking, context=context)
            if test != (need_rereserve, all_op_processed):
                raise osv.except_osv(_('test temps do_transfer!'), "recompute_remaining_qty")
        return (need_rereserve, all_op_processed)

    @api.model
    def add_packop_values(self, vals, prevals):
        self.ensure_one()
        processed_products = set()
        for move in [x for x in self.move_lines if x.state not in ('done', 'cancel')]:
            if move.product_id.id not in processed_products:
                vals += prevals.get(move.product_id.id, [])
                processed_products.add(move.product_id.id)
        return vals

    @api.multi
    def recalculate_forced_qties_with_uom(self):
        forced_qties = {}  # Quantity remaining after calculating reserved quants
        picking_quants = []
        for move in self.move_lines:
            if move.state not in ('assigned', 'confirmed', 'waiting'):
                continue
            move_quants = move.reserved_quant_ids
            picking_quants += move_quants
            forced_qty = 0
            if move.state == 'assigned':
                forced_qty = move.product_uom_qty
                for quant in move_quants:
                    forced_qty -= move.product_id.uom_id._compute_qty_obj(move.product_id.uom_id, quant.qty,
                                                                          move.product_uom)
            # if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
            if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                key = (move.product_id, move.product_uom)
                if forced_qties.get(key):
                    forced_qties[key] += forced_qty
                else:
                    forced_qties[key] = forced_qty
        return forced_qties, picking_quants

    @api.model
    def _prepare_pack_ops(self, picking, quants, forced_qties):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation."""

        def _picking_putaway_apply(product):
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.env['stock.location'].get_putaway_strategy(picking.location_dest_id, product)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # Let's recalculate forced qties to get initial UOMs
        forced_qties, picking_quants = picking.recalculate_forced_qties_with_uom()

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one.
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise Warning(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise Warning(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id

        vals = []
        qtys_grouped = {}
        # for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        # find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(quants_suggested_locations)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quants = self.env['stock.quant'].browse(pack.get_content())
            vals.append({
                'picking_id': picking.id,
                'package_id': pack.id,
                'product_qty': 1.0,
                'location_id': pack.location_id.id,
                'location_dest_id': quants_suggested_locations[pack_quants[0]],
                'owner_id': pack.owner_id.id,
            })
            # remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]

        # Go through all remaining reserved quants and group by product, package, lot, owner, source location and dest
        # location
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.lot_id.id, quant.owner_id.id, quant.location_id.id,
                   dest_location_id, quant.product_id.uom_id.id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for (product, uom), qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, False, picking.owner_id.id, picking.location_id.id, suggested_location_id, uom.id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty

        # Create the necessary operations for the grouped quants and remaining qtys
        prevals = {}
        for key, qty in qtys_grouped.items():
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty,
                'product_id': key[0],
                'package_id': key[1],
                'lot_id': key[2],
                'owner_id': key[3],
                'location_id': key[4],
                'location_dest_id': key[5],
                'product_uom_id': key[6],
            }
            if key[0] in prevals:
                prevals[key[0]].append(val_dict)
            else:
                prevals[key[0]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if
        # possible
        return picking.add_packop_values(vals, prevals)

    @api.cr_uid_context
    def _get_top_level_packages(self, cr, uid, quants_suggested_locations, context=None):
        """This method searches for the higher level packages that can be moved as a single operation, given a list of quants
           to move and their suggested destination, and returns the list of matching packages.
        """
        # Try to find as much as possible top-level packages that can be moved
        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        top_lvl_packages = set()
        quants_to_compare = list(set([x.id for x in quants_suggested_locations.keys() if x and x.id]))
        quants_suggested_locations_improved = {}
        for k, v in quants_suggested_locations.iteritems():
            quants_suggested_locations_improved[k.id] = v
        for pack in list(set([x.package_id for x in quants_suggested_locations.keys() if x and x.package_id])):
            loop = True
            test_pack = pack
            good_pack = False
            pack_destination = False
            while loop:
                pack_quants = pack_obj.get_content(cr, uid, [test_pack.id], context=context)
                all_in = True
                for quant in pack_quants:
                    # If the quant is not in the quants to compare and not in the common location
                    if not quant in quants_to_compare:
                        all_in = False
                        break
                    else:
                        # if putaway strat apply, the destination location of each quant may be
                        # different (and thus the package should not be taken as a single
                        # operation)
                        if not pack_destination:
                            pack_destination = quants_suggested_locations_improved[quant]
                        elif pack_destination != quants_suggested_locations_improved[quant]:
                            all_in = False
                            break
                if all_in:
                    good_pack = test_pack
                    if test_pack.parent_id:
                        test_pack = test_pack.parent_id
                    else:
                        # stop the loop when there's no parent package anymore
                        loop = False
                else:
                    # stop the loop when the package test_pack is not totally reserved for moves of this picking
                    # (some quants may be reserved for other picking or not reserved at all)
                    loop = False
            if good_pack:
                top_lvl_packages.add(good_pack)
        return list(top_lvl_packages)

    @api.model
    def delete_empty_pickings(self):
        self.env.cr.execute("""WITH nb_moves_picking AS (
    SELECT
        sp.id,
        count(sm.id) AS nb_moves
    FROM stock_picking sp
        LEFT JOIN stock_move sm ON sm.picking_id = sp.id
    WHERE sp.state NOT IN ('done', 'cancel')
    GROUP BY sp.id)

SELECT id
FROM nb_moves_picking
WHERE nb_moves = 0""")
        picking_ids = [item[0] for item in self.env.cr.fetchall()]
        if picking_ids:
            pickings = self.env['stock.picking'].browse(picking_ids)
            packops = self.env['stock.pack.operation'].search([('picking_id', 'in', picking_ids)])
            packops.unlink()
            pickings.unlink()

    @api.cr_uid_ids_context
    def _get_pickings_dates_priority(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id and (not (
                move.picking_id.min_date < move.date_expected < move.picking_id.max_date) or
                    move.priority > move.picking_id.priority):
                res.add(move.picking_id.id)
        return list(res)

    def _get_pickings_group_id(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id and move.picking_id.group_id != move.group_id:
                res.add(move.picking_id.id)
        return list(res)

    @api.cr_uid_id_context
    def _set_priority(self, cr, uid, id, field, value, arg, context=None):
        move_obj = self.pool.get("stock.move")
        if value:
            move_ids = [move.id for move in self.browse(cr, uid, id, context=context).move_lines]
            move_obj.write(cr, uid, move_ids, {'priority': value}, context=context)

    @api.cr_uid_id_context
    def _set_min_date(self, cr, uid, id, field, value, arg, context=None):
        move_obj = self.pool.get("stock.move")
        if value:
            if len(value) == 10:
                value += ' 00:00:00'
            move_ids = [move.id for move in self.browse(cr, uid, id, context=context).move_lines]
            move_obj.write(cr, uid, move_ids, {'date_expected': value}, context=context)

    _columns = {
        'priority': osv.fields.function(get_min_max_date, multi="min_max_date", fnct_inv=_set_priority,
                                        type='selection',
                                        selection=procurement.PROCUREMENT_PRIORITIES, string='Priority',
                                        store={
                                            'stock.move': (
                                                _get_pickings_dates_priority, ['priority', 'picking_id'], 20)},
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, select=1,
                                        help="Priority for this picking. Setting manually a value here would set it as "
                                             "priority for all the moves",
                                        track_visibility='onchange', required=True),
        'min_date': osv.fields.function(get_min_max_date, multi="min_max_date", fnct_inv=_set_min_date,
                                        store={'stock.move': (
                                            _get_pickings_dates_priority, ['date_expected', 'picking_id'], 20)},
                                        type='datetime',
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                                        string='Scheduled Date', select=1,
                                        help="Scheduled time for the first part of the shipment to be processed. "
                                             "Setting manually a value here would set it as expected date for all the "
                                             "stock moves.",
                                        track_visibility='onchange'),
        'max_date': osv.fields.function(get_min_max_date, multi="min_max_date",
                                        store={'stock.move': (
                                            _get_pickings_dates_priority, ['date_expected', 'picking_id'], 20)},
                                        type='datetime', string='Max. Expected Date', select=2,
                                        help="Scheduled time for the last part of the shipment to be processed"),
        'group_id': osv.fields.related('move_lines', 'group_id', type='many2one', relation='procurement.group',
                                       string='Procurement Group', readonly=True,
                                       store={
                                           'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_lines'], 10),
                                           'stock.move': (_get_pickings_group_id, ['group_id', 'picking_id'], 10),
                                       }),
    }


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_reserved_availability(self, cr, uid, ids, field_name, args, context=None):
        """Rewritten here to have the database do the sum for us through read_group."""
        res = dict.fromkeys(ids, 0)
        values = self.pool.get('stock.quant').read_group(cr, uid, [('reservation_id', 'in', ids)],
                                                         ['reservation_id', 'qty'], ['reservation_id'], context=context)
        for val in values:
            if val['reservation_id']:
                res[val['reservation_id'][0]] = val['qty']
        return res

    def _get_remaining_qty(self, cr, uid, ids, field_name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        if ids:
            cr.execute("""
                SELECT sm.id,
                max(sm.product_qty) product_qty,
                sum(COALESCE(smol.qty,0)) qty,
                pu.rounding
                FROM stock_move sm
                LEFT JOIN product_product pp ON pp.id = sm.product_id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN stock_move_operation_link smol ON sm.id=smol.move_id
                LEFT JOIN product_uom pu ON pu.id=pt.uom_id
                WHERE sm.id IN %s
                GROUP BY sm.id,pu.rounding
            """, (tuple(ids),))
            moves = cr.fetchall()
            for move in moves:
                qty = move[1] - move[2]
                # Keeping in product default UoM
                res[move[0]] = float_round(qty, precision_rounding=move[3])

        if context.get("test_transfer"):
            test = super(StockMove, self)._get_remaining_qty(cr, uid, ids, field_name, args,
                                                             context=context)
            if len(test) == len(res):

                for item in test.keys():
                    if float_compare(test[item], res[item],
                                     precision_rounding=self.pool.get('stock.move').browse(cr, uid, [item],
                                                                                           context)[
                                         0].product_id.uom_id.rounding) != 0:
                        raise osv.except_osv(_('test non regression'), "_get_remaining_qty")
            else:
                raise osv.except_osv(_('test non regression!'), "la valeur n'a pas la meme longueur")

        return res

    _columns = {
        'reserved_availability': old_api_fields.function(_get_reserved_availability, type='float',
                                                         string='Quantity Reserved', readonly=True,
                                                         help='Quantity that has already been reserved for this move'),
        'remaining_qty': old_api_fields.function(_get_remaining_qty, type='float', string='Remaining Quantity',
                                                 digits=0,
                                                 states={'done': [('readonly', True)]},
                                                 help="Remaining Quantity in default UoM according to operations matched with this move"),
    }

    defer_picking_assign = fields.Boolean("Defer Picking Assignement", default=False,
                                          help="If checked, the stock move will be assigned to a picking only if there "
                                               "is available quants in the source location. Otherwise, it will be "
                                               "assigned a picking as soon as the move is confirmed.")

    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        """Assigns these moves that share the same procurement.group, location_from and location_to to a stock picking.

        Overridden here to assign only if the move is prereserved.
        :<param procurement_group: The procurement.group of the moves
        :param location_from: The source location of the moves
        :param location_to: The destination lcoation of the moves
        """
        self.env.cr.execute(SQL_REQUEST_BY_MOVE, (tuple(self.ids), tuple(self.ids), tuple(self.ids)))
        prereservations = self.env.cr.fetchall()
        prereserved_move_ids = [p[0] for p in prereservations]
        not_deferred_moves = self.filtered(lambda m: m.defer_picking_assign is False)
        todo_moves = not_deferred_moves | self.browse(prereserved_move_ids)
        # Only assign prereserved or outgoing moves to pickings
        if todo_moves:
            return super(StockMove, todo_moves)._picking_assign(procurement_group, location_from, location_to)
        else:
            return True

    @api.multi
    def assign_to_picking(self):
        """Assign the moves to an appropriate picking (or not)."""
        todo_map = {}
        for move in self:
            key = (move.group_id.id, move.location_id.id, move.location_dest_id.id, move.picking_type_id.id)
            if key not in todo_map:
                todo_map[key] = self.env['stock.move']
            todo_map[key] |= move
        for key, moves in todo_map.iteritems():
            procurement_group, location_from, location_to, _ = key
            moves._picking_assign(procurement_group, location_from, location_to)

    @api.multi
    def action_assign(self):
        """ Checks the product type and accordingly writes the state.
        Overridden here to also assign a picking if it is not done yet.
        """
        # moves_no_pick = self.filtered(lambda m: m.picking_type_id and not m.picking_id)
        moves_no_pick = self.search([
            ('id', 'in', self.ids), ('picking_type_id', '!=', False), ('picking_id', '=', False)])
        moves_no_pick.assign_to_picking()
        return super(StockMove, self).action_assign()


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    defer_picking_assign = fields.Boolean("Defer Picking Assignement", default=False,
                                          help="If checked, the stock move generated by this rule will be assigned to "
                                               "a picking only if there is available quants in the source location. "
                                               "Otherwise, it will be assigned a picking as soon as the move is "
                                               "confirmed.")


class StockLocationPath(models.Model):
    _inherit = 'stock.location.path'

    defer_picking_assign = fields.Boolean("Defer Picking Assignement", default=False,
                                          help="If checked, the stock move generated by this rule will be assigned to "
                                               "a picking only if there is available quants in the source location. "
                                               "Otherwise, it will be assigned a picking as soon as the move is "
                                               "confirmed.")

    @api.model
    def _prepare_push_apply(self, rule, move):
        res = super(StockLocationPath, self)._prepare_push_apply(rule, move)
        res.update({'defer_picking_assign': rule.defer_picking_assign})
        return res


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _run_move_create(self, procurement):
        res = super(ProcurementOrder, self)._run_move_create(procurement)
        res.update({'defer_picking_assign': procurement.rule_id.defer_picking_assign})
        return res

    @api.model
    def run_assign_moves(self):
        dom = [('reserved', '=', False)]
        if self.env.context.get('assign_in_location_ids'):
            dom += [('location_id', 'in', self.env.context['assign_in_location_ids'])]
        if self.env.context.get('no_assign_in_location_ids'):
            dom += [('location_id', 'not in', self.env.context['no_assign_in_location_ids'])]
        prereservations = self.env['stock.prereservation'].search(dom)
        confirmed_move_ids = prereservations.read(['move_id'], load=False)
        move_ids = [cm['id'] for cm in confirmed_move_ids]
        confirmed_moves = self.env['stock.move'].search([('id', 'in', move_ids)], limit=None,
                                                        order='priority desc, date_expected asc, id')
        cm_product_ids = confirmed_moves.read(['id', 'product_id'], load=False)

        # Create a dict of moves with same product {product_id: [move_id, move_id], product_id: []}
        result = dict()
        for row in cm_product_ids:
            if row['product_id'] not in result:
                result[row['product_id']] = list()
            result[row['product_id']].append(row['id'])
        product_ids = result.values()

        while product_ids:
            products = product_ids[:PRODUCT_CHUNK]
            product_ids = product_ids[PRODUCT_CHUNK:]
            move_ids = flatten(products)
            if self.env.context.get('jobify'):
                assign_moves.delay(ConnectorSession.from_env(self.env), 'stock.move', move_ids, dict(self.env.context))
            else:
                assign_moves(ConnectorSession.from_env(self.env), 'stock.move', move_ids, dict(self.env.context))


class StockPrereservation(models.Model):
    _name = 'stock.prereservation'
    _description = "Stock Pre-Reservation"
    _auto = False

    move_id = fields.Many2one('stock.move', readonly=True, index=True)
    location_id = fields.Many2one('stock.location', readonly=True, index=True)
    picking_id = fields.Many2one('stock.picking', readonly=True, index=True)
    reserved = fields.Boolean("Move has reserved quants", readonly=True, index=True)

    def init(self, cr):
        drop_view_if_exists(cr, "stock_prereservation")
        cr.execute("""
        CREATE OR REPLACE VIEW stock_prereservation AS (
            WITH RECURSIVE top_parent(loc_id, top_parent_id) AS (
                SELECT
                    sl.id AS loc_id, sl.id AS top_parent_id
                FROM
                    stock_location sl
                    LEFT JOIN stock_location slp ON sl.location_id = slp.id
                WHERE
                    sl.usage='internal'
            UNION
                SELECT
                    sl.id AS loc_id, tp.top_parent_id
                FROM
                    stock_location sl, top_parent tp
                WHERE
                    sl.usage='internal' AND sl.location_id=tp.loc_id
            ),

            confirmed_moves_with_picking_type AS (
                SELECT
                    id,
                    state,
                    picking_id,
                    location_id,
                    location_dest_id,
                    product_id,
                    product_qty,
                    priority,
                    date_expected
                FROM stock_move
                WHERE picking_type_id IS NOT NULL
                      AND state='confirmed'
            ),

            moves_with_quants_reserved AS (
                SELECT
                    sm.id,
                    sm.location_id,
                    sm.picking_type_id,
                    sm.picking_id
                FROM stock_move sm
                INNER JOIN stock_quant sq ON sq.reservation_id=sm.id
                GROUP BY sm.id
            ),

            move_qties_interm AS (
                SELECT
                    sm.id AS move_id,
                    sm.picking_id,
                    sm.location_id,
                    sm.product_id,
                    sum(sm.product_qty) OVER (
                        PARTITION BY sm.product_id, sm.location_id, sm.location_dest_id
                        ORDER BY sm.priority DESC, sm.date_expected, sm.id
                    ) - sm.product_qty AS qty
                FROM confirmed_moves_with_picking_type sm
                LEFT JOIN stock_quant sq ON sq.reservation_id=sm.id
                WHERE sq.id IS NULL
            ),

            not_reserved_quantities AS (
                SELECT
                    tp.top_parent_id AS location_id,
                    sq.product_id,
                    sum(sq.qty) AS qty
                FROM stock_quant sq
                LEFT JOIN top_parent tp ON tp.loc_id=sq.location_id
                WHERE tp.top_parent_id IN (SELECT location_id FROM move_qties_interm) AND sq.reservation_id IS NULL
                GROUP BY tp.top_parent_id, sq.product_id
            ),

            move_qties AS (
                SELECT
                    mqi.*,
                    nrq.qty AS sum_qty
                FROM move_qties_interm mqi
                LEFT JOIN
                  not_reserved_quantities nrq ON nrq.product_id=mqi.product_id AND nrq.location_id=mqi.location_id
            )

            SELECT
                foo.move_id AS id,
                foo.move_id,
                foo.location_id,
                foo.picking_id,
                foo.reserved
            FROM (
                    SELECT
                        sm.id AS move_id,
                        sm.location_id AS location_id,
                        sm.picking_id AS picking_id,
                        TRUE AS reserved
                    FROM
                        moves_with_quants_reserved sm
                    WHERE sm.picking_type_id IS NOT NULL
                UNION ALL
                    SELECT DISTINCT
                        sm.id AS move_id,
                        sm.location_id AS location_id,
                        sm.picking_id AS picking_id,
                        FALSE AS reserved
                    FROM
                        stock_move sm
                        LEFT JOIN stock_move smp ON smp.move_dest_id = sm.id
                        LEFT JOIN stock_move sms ON sm.split_from = sms.id
                        LEFT JOIN stock_move smps ON smps.move_dest_id = sms.id
                    WHERE
                        sm.state = 'waiting'
                        AND sm.picking_type_id IS NOT NULL
                        AND (smp.state = 'done' OR smps.state = 'done')
                UNION ALL
                    SELECT
                        mq.move_id,
                        mq.location_id,
                        mq.picking_id,
                        FALSE AS reserved
                    FROM move_qties mq
                    WHERE mq.qty <= mq.sum_qty
                UNION ALL
                    SELECT
                        sm.id          AS move_id,
                        sm.location_id AS location_id,
                        sm.picking_id  AS picking_id,
                        FALSE          AS reserved
                    FROM stock_move sm
                    WHERE sm.state = 'confirmed'
                        AND sm.picking_type_id IS NOT NULL
                        AND sm.picking_id IS NULL
                        AND sm.defer_picking_assign = FALSE
            ) foo
        )
        """)


class ConfirmProcessPrereservations(models.TransientModel):
    _name = 'confirm.process.prereservations'

    @api.multi
    def confirm(self):
        self.env['stock.picking'].process_prereservations()


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    @api.model
    def _resolve_inventory_line(self, inventory_line):
        if float_compare(inventory_line.theoretical_qty, inventory_line.product_qty,
                         precision_rounding=inventory_line.product_id.uom_id.rounding) > 0:
            domain = [('qty', '>', 0.0), ('package_id', '=', inventory_line.package_id.id),
                      ('lot_id', '=', inventory_line.prod_lot_id.id),
                      ('location_id', '=', inventory_line.location_id.id),
                      ('product_id', '=', inventory_line.product_id.id)]
            not_reserved_quants = self.env['stock.quant'].search(domain + [('reservation_id', '=', False)])
            not_reserved_qty = sum([quant.qty for quant in not_reserved_quants])
            if float_compare(not_reserved_qty, inventory_line.theoretical_qty - inventory_line.product_qty,
                             precision_rounding=inventory_line.product_id.uom_id.rounding) < 0:
                reserved_quants = self.env['stock.quant'].search(domain + [('reservation_id', '!=', False)])
                moves_to_unreserve = self.env['stock.move']
                for quant in reserved_quants:
                    moves_to_unreserve |= quant.reservation_id
                if moves_to_unreserve:
                    moves_to_unreserve.do_unreserve()
        return super(StockInventoryLine, self)._resolve_inventory_line(inventory_line)
