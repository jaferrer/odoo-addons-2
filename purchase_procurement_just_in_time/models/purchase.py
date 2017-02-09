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

from datetime import datetime
from openerp import fields, models, api, _, exceptions
from openerp.tools.float_utils import float_compare
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, float_round


class PurchaseOrderJustInTime(models.Model):
    _inherit = 'purchase.order'

    order_line = fields.One2many(states={'done': [('readonly', True)]})
    date_order_max = fields.Datetime(string="Maximum order date", readonly=True,
                                     help="This is the latest date an order line inside this PO must be ordered. "
                                          "PO lines with an order date beyond this date must be grouped in a later PO. "
                                          "This date is set according to the supplier order_group_period and to this "
                                          "PO order date.")
    group_id = fields.Many2one('procurement.group', string="Procurement Group", readonly=True)
    date_order = fields.Datetime(required=False)

    @api.model
    def _create_stock_moves(self, order, order_lines, picking_id=False):
        """
        Creates missing stock moves for the given order_lines.
        :param order: purchase.order
        :param order_lines: recordset of purchase.order.lines
        :param group_id: id of procurement.group
        :param picking_id: id of stock.picking
        """
        todo_moves = self.env['stock.move']
        group = self.env['procurement.group'].search([('name', '=', order.name),
                                                      ('partner_id', '=', order.partner_id.id)], limit=1)
        if not group:
            group = self.env['procurement.group'].create({'name': order.name,
                                                          'partner_id': order.partner_id.id})
        group_id = group.id

        for order_line in order_lines:
            if not order_line.product_id:
                continue

            if order_line.product_id.type in ('product', 'consu'):
                for vals in self._prepare_order_line_move(order, order_line, picking_id, group_id):
                    move = self.env['stock.move'].create(vals)
                    todo_moves |= move
        todo_moves.with_context(mail_notrack=True).action_confirm()
        todo_moves.with_context(mail_notrack=True).force_assign()

    @api.model
    def _prepare_order_line_move(self, order, order_line, picking_id, group_id):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be
        used in stock.move's create()'''
        product_uom = self.env['product.uom']
        price_unit = order_line.price_unit
        if order_line.taxes_id:
            taxes = order_line.taxes_id.compute_all(price_unit, 1.0, order_line.product_id, order.partner_id)
            price_unit = taxes['total']
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        if order.currency_id.id != order.company_id.currency_id.id:
            # we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
            price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
        res = []
        if order.location_id.usage == 'customer':
            name = order_line.product_id.with_context(lang=order.dest_address_id.lang).display_name
        else:
            name = order_line.name or ''
        move_template = {
            'name': name,
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order.date_order,
            'date_expected': order_line.date_planned + ' 01:00:00',
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': order.picking_type_id.id,
            'group_id': group_id,
            'procurement_id': False,
            'origin': order.name,
            'route_ids': order.picking_type_id.warehouse_id and [
                (6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': order.picking_type_id.warehouse_id.id,
            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
            'propagate': True,
        }

        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            if procurement.move_ids:
                # Remove data if proc already has a move
                for move in procurement.move_ids:
                    if move.state in ['draft', 'cancel']:
                        continue
                    if move.purchase_line_id == order_line:
                        move_qty_in_pol_uom = product_uom._compute_qty(move.product_uom.id, move.product_uom_qty,
                                                                       to_uom_id=order_line.product_uom.id)
                        diff_quantity -= move_qty_in_pol_uom
                    else:
                        line_to_check = move.purchase_line_id
                        move.procurement_id = False
                        line_to_check.adjust_move_no_proc_qty()
                continue
            if procurement.state in ['done', 'cancel']:
                # Done or cancel proc without moves
                continue
            procurement_qty = product_uom._compute_qty(procurement.product_uom.id, procurement.product_qty,
                                                       to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            min_qty = min(procurement_qty, diff_quantity)
            rounded_min_qty = float_round(min_qty, precision_rounding=order_line.product_uom.rounding)
            if float_compare(rounded_min_qty, 0.0, precision_rounding=order_line.product_uom.rounding) != 0:
                tmp.update({
                    'product_uom_qty': rounded_min_qty,
                    'product_uos_qty': rounded_min_qty,
                    'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                    'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
                    'procurement_id': procurement.id,
                    'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
                    'propagate': procurement.rule_id.propagate,
                })
                res.append(tmp)
            diff_quantity -= min_qty
        # if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
        # split the future stock move in two because the route followed may be different.
        for move in order_line.move_ids:
            if move.state in ['draft', 'cancel'] or move.procurement_id:
                continue
            move_qty_in_pol_uom = product_uom._compute_qty(move.product_uom.id, move.product_uom_qty,
                                                           to_uom_id=order_line.product_uom.id)
            diff_quantity -= move_qty_in_pol_uom
        rounded_diff_qty = float_round(diff_quantity, precision_rounding=order_line.product_uom.rounding)
        if float_compare(rounded_diff_qty, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
            move_template['product_uom_qty'] = rounded_diff_qty
            move_template['product_uos_qty'] = rounded_diff_qty
            res.append(move_template)
        return res

    @api.model
    def get_purchase_order_states_with_moves(self):
        return ['approved']

    @api.multi
    def action_cancel(self):
        order_line_ids = []
        for rec in self:
            order_line_ids += rec.order_line.ids
        running_procs = self.env['procurement.order'].search([('purchase_line_id', 'in', order_line_ids),
                                                              ('state', '=', 'running')])
        moves_no_procs = self.env['stock.move'].search([('purchase_line_id', 'in', order_line_ids),
                                                        ('procurement_id', '=', False)])
        # We explicitly cancel moves without procurements so that move_dest_id get cancelled too in this case
        moves_no_procs.action_cancel()
        # For the other moves, we don't want the move_dest_id to be cancelled, so we pass cancel_procurement
        res = super(PurchaseOrderJustInTime, self.with_context(cancel_procurement=True)).action_cancel()
        running_procs.remove_procs_from_lines(unlink_moves_to_procs=True)
        return res

    @api.multi
    def set_order_line_status(self, status):
        # Overwritten here to prevent any cancelled proc to reach 'exception' state when a purchase order in cancelled
        order_line_ids = self.env['purchase.order.line']
        for order in self:
            if status in ('draft', 'cancel'):
                order_line_ids += order.order_line
            else:  # Do not change the status of already cancelled lines
                order_line_ids += order.order_line.filtered(lambda line: line.state != 'cancel')
        if order_line_ids:
            order_line_ids.write({'state': status})
        if order_line_ids and status == 'cancel':
            procs = self.env['procurement.order'].search([('purchase_line_id', 'in', order_line_ids.ids),
                                                          ('state', 'not in', ['cancel', 'done'])])
            if procs:
                procs.write({'state': 'exception'})
        return True

    @api.multi
    def unlink(self):
        order_line_ids = []
        for rec in self:
            order_line_ids += rec.order_line.ids
        running_procs = self.env['procurement.order'].search([('purchase_line_id', 'in', order_line_ids),
                                                              ('state', '=', 'running')])
        moves_no_procs = self.env['stock.move'].search([('purchase_line_id', 'in', order_line_ids),
                                                        ('procurement_id', '=', False)])
        # We explicitly cancel moves without procurements so that move_dest_id get cancelled too in this case
        moves_no_procs.action_cancel()
        # For the other moves, we don't want the move_dest_id to be cancelled, so we pass cancel_procurement
        res = super(PurchaseOrderJustInTime, self.with_context(cancel_procurement=True)).unlink()
        running_procs.remove_procs_from_lines(unlink_moves_to_procs=True)
        return res

    @api.multi
    def reset_to_confirmed(self):
        for rec in self:
            rec.signal_workflow('except_to_confirmed')
            if rec.state in self.get_purchase_order_states_with_moves():
                for line in rec.order_line:
                    line.adjust_moves_qties(line.product_qty)


class PurchaseOrderLineJustInTime(models.Model):
    _inherit = 'purchase.order.line'
    _order = 'order_id, line_no, id'

    supplier_code = fields.Char(string="Supplier Code", compute='_compute_supplier_code')
    ack_ref = fields.Char("Acknowledge Reference", help="Reference of the supplier's last reply to confirm the delivery"
                                                        " at the planned date")
    date_ack = fields.Date("Last Acknowledge Date",
                           helps="Last date at which the supplier confirmed the delivery at the planned date.")
    opmsg_type = fields.Selection([('no_msg', "Ok"), ('late', "LATE"), ('early', "EARLY"), ('reduce', "REDUCE"),
                                   ('to_cancel', "CANCEL")], compute="_compute_opmsg", string="Message Type")
    opmsg_delay = fields.Integer("Message Delay", compute="_compute_opmsg")
    opmsg_reduce_qty = fields.Float("New target quantity after procurement cancellation", readonly=True, default=False)
    opmsg_text = fields.Char("Operational message", compute="_compute_opmsg_text",
                             help="This field holds the operational messages generated by the system to the operator")
    remaining_qty = fields.Float("Remaining quantity", help="Quantity not yet delivered by the supplier",
                                 compute="_get_remaining_qty", store=True)
    to_delete = fields.Boolean('True if all the procurements of the purchase order line are canceled')
    father_line_id = fields.Many2one('purchase.order.line', string="Very first line splited", readonly=True)
    children_line_ids = fields.One2many('purchase.order.line', 'father_line_id', string="Children lines")
    children_number = fields.Integer(string="Number of children", readonly=True, compute='_compute_children_number')

    @api.depends('date_planned', 'date_required', 'to_delete', 'product_qty', 'opmsg_reduce_qty')
    def _compute_opmsg(self):
        """
        Sets parameters date_planned, date_required, and opmsg_type.
        """

        for rec in self:
            if rec.date_planned and rec.date_required:
                date_planned = datetime.strptime(rec.date_planned, DEFAULT_SERVER_DATE_FORMAT)
                date_required = datetime.strptime(rec.date_required, DEFAULT_SERVER_DATE_FORMAT)
                min_late_days = int(self.env['ir.config_parameter'].get_param(
                    "purchase_procurement_just_in_time.opmsg_min_late_delay"))
                min_early_days = int(self.env['ir.config_parameter'].get_param(
                    "purchase_procurement_just_in_time.opmsg_min_early_delay"))
                if date_planned >= date_required:
                    delta = date_planned - date_required
                    if delta.days >= min_late_days:
                        rec.opmsg_type = 'late'
                        rec.opmsg_delay = delta.days
                else:
                    delta = date_required - date_planned
                    if delta.days >= min_early_days:
                        rec.opmsg_type = 'early'
                        rec.opmsg_delay = delta.days
            if rec.to_delete and rec.product_qty != 0:
                rec.opmsg_type = 'to_cancel'
            if not rec.to_delete and rec.opmsg_reduce_qty and rec.opmsg_reduce_qty < rec.product_qty:
                rec.opmsg_type = 'reduce'

    @api.depends('opmsg_type', 'opmsg_delay', 'opmsg_reduce_qty', 'product_qty', 'to_delete', 'state')
    def _compute_opmsg_text(self):
        """
        Sets parameters opmsg_type, opmsg_delay, opmsg_reduce_qty, product_qty, to_delete and state.
        """

        for rec in self:
            msg = ""
            if rec.to_delete and rec.product_qty != 0:
                msg += _("CANCEL LINE")
            if not rec.to_delete and rec.opmsg_reduce_qty and rec.opmsg_reduce_qty < rec.product_qty:
                msg += _("REDUCE QTY to %.1f %s ") % (rec.opmsg_reduce_qty, rec.product_uom.name)
            if rec.opmsg_type == 'early':
                msg += _("EARLY by %i day(s)") % rec.opmsg_delay
            elif rec.opmsg_type == 'late':
                msg += _("LATE by %i day(s)") % rec.opmsg_delay
            rec.opmsg_text = msg

    @api.multi
    @api.depends('partner_id', 'product_id')
    def _compute_supplier_code(self):
        for rec in self:
            list_supinfos = self.env['product.supplierinfo'].search(
                [('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id), ('name', '=', rec.partner_id.id)]
            )
            if list_supinfos:
                rec.supplier_code = list_supinfos[0].product_code

    @api.depends('product_qty', 'move_ids', 'move_ids.product_uom_qty', 'move_ids.product_uom', 'move_ids.state')
    def _get_remaining_qty(self):
        """
        Calculates ramaining_qty
        """
        for rec in self:
            delivered_qty = sum([self.env['product.uom']._compute_qty(move.product_uom.id, move.product_uom_qty,
                                                                      rec.product_uom.id)
                                 for move in rec.move_ids if move.state == 'done'])
            rec.remaining_qty = float_round(rec.product_qty - delivered_qty,
                                            precision_rounding=rec.product_uom.rounding)

    @api.depends('children_line_ids')
    def _compute_children_number(self):
        """
        Calculates children_number
        """
        for rec in self:
            rec.children_number = len(rec.children_line_ids)

    @api.multi
    def open_form_purchase_order_line(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'name': _("Purchase Order Line: %s") % self.line_no,
            'views': [(False, "form")],
            'res_id': self.id,
            'context': {}
        }

    @api.model
    def create(self, vals):
        """
        Improves original function create. Sets automatically a line number and creates appropriate moves in a picking.
        :return: the same result as original create function
        """

        result = super(PurchaseOrderLineJustInTime, self).create(vals)
        if result.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
            result.order_id.set_order_line_status('confirmed')
            if float_compare(result.product_qty, 0.0, precision_rounding=result.product_uom.rounding) != 0 and \
                    not result.move_ids and not self.env.context.get('no_update_moves'):
                # We create associated moves
                self.env['purchase.order']._create_stock_moves(result.order_id, result)
        return result

    @api.multi
    def adjust_moves_qties(self, target_qty):
        """
        Progressively delete the moves linked with no procurements, then detach the other ones until the global
        quantity ordered is lower or equal to the new quantity.
        Then, if it is lower, we create a new move as before, to reach the appropriate quantity.

        :param target_qty: new quantity of the purchase order line
        """
        self.ensure_one()

        moves_without_proc_id = self.move_ids.filtered(
            lambda m: m.state not in ['done', 'cancel'] and not m.procurement_id).sorted(key=lambda m: m.product_qty,
                                                                                         reverse=True)
        moves_with_proc_id = self.move_ids.filtered(
            lambda m: m.state not in ['done', 'cancel'] and m.procurement_id).sorted(key=lambda m: m.product_qty,
                                                                                     reverse=True)
        qty_not_cancelled_moves = sum([x.product_qty for x in self.move_ids if x.state != 'cancel'])
        qty_moves_no_proc = sum([x.product_qty for x in moves_without_proc_id])
        qty_not_cancelled_moves_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                               qty_not_cancelled_moves,
                                                                               self.product_uom.id)
        qty_moves_no_proc_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                         qty_moves_no_proc,
                                                                         self.product_uom.id)

        qty_to_remove = qty_not_cancelled_moves_pol_uom - qty_moves_no_proc_pol_uom - target_qty
        to_detach_procs = self.env['procurement.order']

        while qty_to_remove > 0 and moves_with_proc_id:
            move = moves_with_proc_id[0]
            moves_with_proc_id -= move
            to_detach_procs |= move.procurement_id
            qty_to_remove -= self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                  move.product_qty,
                                                                  self.product_uom.id)

        to_detach_procs.remove_procs_from_lines(unlink_moves_to_procs=True)
        self.adjust_move_no_proc_qty()

    def adjust_move_no_proc_qty(self):
        """Adjusts the quantity of the move without proc, recreating it if necessary."""
        moves_no_procs = self.env['stock.move'].search(
            [('purchase_line_id', 'in', self.ids),
             ('procurement_id', '=', False),
             ('state', 'not in', ['done', 'cancel'])]).with_context(mail_notrack=True)
        # Dirty hack to keep the moves so that we don't to set the PO in shipping except
        # but still compute the correct qty in _create_stock_moves
        moves_no_procs.write({'product_uom_qty': 0})
        for rec in self:
            self.env['purchase.order']._create_stock_moves(rec.order_id, rec)

        # We don't want cancel_procurement context here,
        # because we want to cancel next move too (no procs).
        moves_no_procs.action_cancel()
        moves_no_procs.unlink()

    @api.multi
    def update_moves(self, vals):
        """
        Updates moves associated to a purchase order line, based on the procurement order associated to this line.
        When increasing quantity: if any move is linked with no procurement, we increase its quantity. If not, we
        create a new move.
        When decreasing a quantity, we progressively delete the moves linked with no procurements, then detach the other
        ones until the global quantity ordered is lower or equal to the new quantity. Then, if it is lower, we create a
        new move as before, to reach the appropriate quantity.
        """
        self.ensure_one()
        product = self.env['product.product'].browse(vals.get('product_id', self.product_id.id))
        uom = self.env['product.uom'].browse(vals.get('product_uom', self.product_uom.id))
        qty_done = sum([x.product_qty for x in self.move_ids if x.state == 'done'])
        qty_done_pol_uom = self.env['product.uom']._compute_qty(product.uom_id.id, qty_done, uom.id)
        if vals['product_qty'] < qty_done_pol_uom:
            raise exceptions.except_orm(_('Error!'), _("Impossible to cancel moves at state done."))
        if self.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
            self.adjust_moves_qties(vals['product_qty'])
        elif self.state == 'draft':
            sum_procs = sum([self.env['product.uom']._compute_qty(product.uom_id.id, p.product_qty, uom.id) for
                             p in self.procurement_ids])
            # We remove procs if there qty is above the line
            for proc in self.procurement_ids. \
                    sorted(key=lambda m: self.env['product.uom'].
                    _compute_qty(product.uom_id.id, m.product_qty, uom.id), reverse=True):
                if float_compare(vals['product_qty'], sum_procs, precision_rounding=uom.rounding) >= 0:
                    break
                proc.remove_procs_from_lines()
                sum_procs -= proc.product_qty

    @api.multi
    def write(self, vals):
        """
        Improves the original write function. Allows to update moves of a purchase order line even if it is confirmed.
        :return: the same result as original write function
        """

        result = super(PurchaseOrderLineJustInTime, self).write(vals)
        for rec in self:
            if 'product_qty' in vals.keys() and not self.env.context.get('no_update_moves'):
                rec.update_moves(vals)
        if vals.get('price_unit'):
            for rec in self:
                active_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                              ('purchase_line_id', '=', rec.id),
                                                              ('state', 'not in', ['draft', 'cancel', 'done'])])
                active_moves.write({'price_unit': vals['price_unit']})
        return result

    @api.multi
    def act_windows_view_graph(self):
        self.ensure_one()
        warehouses = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)])
        if warehouses:
            wid = warehouses[0].id
        else:
            raise exceptions.except_orm(_("Error!"), _("Your company does not have a warehouse"))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.levels.report',
            'name': _("Stock Evolution"),
            'view_type': 'form',
            'view_mode': 'graph,tree',
            'context': {'search_default_warehouse_id': wid,
                        'search_default_product_id': self.product_id.id}
        }

    @api.multi
    def unlink(self):
        procurements_to_detach = self.env['procurement.order'].search([('purchase_line_id', 'in', self.ids)])
        cancelled_procs = self.env['procurement.order'].search([('purchase_line_id', 'in', self.ids),
                                                                ('state', '=', 'cancel')])
        result = super(PurchaseOrderLineJustInTime, self.with_context(tracking_disable=True)).unlink()
        # We reset initially cancelled procs to state 'cancel', because the unlink function of module purchase would
        # have set them to state 'exception'
        cancelled_procs.with_context(tracking_disable=True).write({'state': 'cancel'})
        procurements_to_detach.remove_procs_from_lines(unlink_moves_to_procs=True)
        return result
