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

from openerp.tools import drop_view_if_exists, flatten, float_round
from openerp import fields, models, api, osv

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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

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

    defer_picking_assign = fields.Boolean("Defer Picking Assignement", default=False,
                                          help="If checked, the stock move will be assigned to a picking only if there "
                                               "is available quants in the source location. Otherwise, it will be "
                                               "assigned a picking as soon as the move is confirmed.")
    reserved_availability = fields.Float(compute='_get_reserved_availability')

    @api.multi
    @api.depends('reserved_quant_ids')
    def _get_reserved_availability(self):
        """Rewritten here to have the database do the sum for us through read_group."""
        values = self.env['stock.quant'].read_group([('reservation_id', 'in', self.ids)], ['reservation_id', 'qty'],
                                                    ['reservation_id'])
        for val in values:
            move = self.search([('id', '=', val['reservation_id'][0])])
            move.reserved_availability = val['qty']

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
            # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
            # In the next version, the locations on the picking should be stored again.
            query = """
                SELECT stock_picking.id FROM stock_picking, stock_move
                WHERE
                    stock_picking.state IN ('draft','waiting','confirmed','partially_available','assigned') AND
                    stock_move.picking_id = stock_picking.id AND
                    stock_picking.picking_type_id = %s AND
                    stock_move.location_id = %s AND
                    stock_move.location_dest_id = %s AND
            """
            params = (todo_moves[0].picking_type_id.id, location_from, location_to)
            if not procurement_group:
                query += "stock_picking.group_id IS NULL LIMIT 1"
            else:
                query += "stock_picking.group_id = %s LIMIT 1"
                params += (procurement_group,)
            self.env.cr.execute(query, params)
            [pick_id] = self.env.cr.fetchone() or [None]
            if not pick_id:
                move = self[0]
                values = {
                    'origin': move.origin,
                    'company_id': move.company_id and move.company_id.id or False,
                    'move_type': move.group_id and move.group_id.move_type or 'direct',
                    'partner_id': move.partner_id.id or False,
                    'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
                }
                pick = self.env['stock.picking'].create(values)
                pick_id = pick.id
            pick_list = self.env.context.get('only_pickings')
            if pick_list and pick_id not in pick_list:
                # Don't assign the move to a picking that is not our picking.
                return True
            return self.with_context(mail_notrack=True).write({'picking_id': pick_id})
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
        moves_no_pick = self.filtered(lambda m: m.picking_type_id and not m.picking_id)
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
        prereservations = self.env['stock.prereservation'].search([('reserved', '=', False)])
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
                assign_moves.delay(ConnectorSession.from_env(self.env), 'stock.move', move_ids, self.env.context)
            else:
                assign_moves(ConnectorSession.from_env(self.env), 'stock.move', move_ids, self.env.context)


class StockPrereservation(models.Model):
    _name = 'stock.prereservation'
    _description = "Stock Pre-Reservation"
    _auto = False

    move_id = fields.Many2one('stock.move', readonly=True, index=True)
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
                      AND defer_picking_assign = TRUE
            ),

            moves_with_quants_reserved AS (
                SELECT
                    sm.id,
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
                foo.picking_id,
                foo.reserved
            FROM (
                    SELECT
                        sm.id AS move_id,
                        sm.picking_id AS picking_id,
                        TRUE AS reserved
                    FROM
                        moves_with_quants_reserved sm
                    WHERE sm.picking_type_id IS NOT NULL
                UNION ALL
                    SELECT DISTINCT
                        sm.id AS move_id,
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
                        mq.picking_id,
                        FALSE AS reserved
                    FROM move_qties mq
                    WHERE mq.qty <= mq.sum_qty
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
            ) foo
        )
        """)
