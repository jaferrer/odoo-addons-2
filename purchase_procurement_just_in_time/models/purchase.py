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

from openerp import fields, models, api, _, exceptions
from openerp.tools import float_round
from openerp.tools.float_utils import float_compare


class PurchaseOrderJustInTime(models.Model):
    _inherit = 'purchase.order'

    order_line = fields.One2many(states={'done': [('readonly', True)]})
    date_order_max = fields.Datetime(string="Maximum order date", readonly=True,
                                     help="This is the latest date an order line inside this PO must be ordered. "
                                          "PO lines with an order date beyond this date must be grouped in a later PO. "
                                          "This date is set according to the supplier order_group_period and to this "
                                          "PO order date.")
    group_id = fields.Many2one('procurement.group', string="Procurement Group", readonly=True)
    date_order = fields.Datetime(required=False, string="Start date for grouping period")

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
                    move = self.env['stock.move'].with_context(mail_notrack=True).create(vals)
                    todo_moves |= move
        todo_moves.with_context(mail_notrack=True).action_confirm()
        todo_moves.with_context(mail_notrack=True).force_assign()

    @api.model
    def _prepare_order_line_move(self, order, order_line, picking_id, group_id):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be
        used in stock.move's create()'''
        price_unit = order_line.get_move_unit_price_from_line(order)
        if order.location_id.usage == 'customer':
            name = order_line.product_id.with_context(lang=order.dest_address_id.lang).display_name
        else:
            name = order_line.name or ''
        existing_quantity = sum([self.env['product.uom']._compute_qty(move.product_uom.id, move.product_uom_qty,
                                                                      order_line.product_uom.id) for move in
                                 order_line.move_ids if move.state != 'cancel'])
        qty_to_add = float_round(order_line.product_qty - existing_quantity,
                                 precision_rounding=order_line.product_uom.rounding)
        if float_compare(qty_to_add, 0.0, precision_rounding=order_line.product_uom.rounding) == 0:
            return []
        return [{
            'name': name,
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'product_uom_qty': qty_to_add,
            'product_uos_qty': qty_to_add,
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
        }]

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
        result = super(PurchaseOrderJustInTime, self.with_context(cancel_procurement=True)).action_cancel()
        running_procs.remove_procs_from_lines()
        return result

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
        res = super(PurchaseOrderJustInTime, self.with_context(cancel_procurement=True)).unlink()
        running_procs.remove_procs_from_lines()
        return res

    @api.multi
    def reset_to_confirmed(self):
        for rec in self:
            rec.signal_workflow('except_to_confirmed')
            if rec.state in self.get_purchase_order_states_with_moves():
                for line in rec.order_line:
                    line.adjust_moves_qties(line.product_qty)

    @api.multi
    def all_pickings_done_or_cancel(self):
        for purchase in self:
            for picking in purchase.picking_ids:
                if picking.state not in ['done', 'cancel']:
                    return False
        return True

    @api.multi
    def order_totally_received(self):
        for purchase in self:
            for order_line in purchase.order_line:
                if float_compare(order_line.remaining_qty, 0, precision_rounding=order_line.product_uom.rounding) > 0:
                    return False
        return True

    @api.multi
    def test_moves_done(self):
        """PO is done at the delivery side if all the pickings are done or cancel, and order not totally received."""
        if self.all_pickings_done_or_cancel():
            if self.order_totally_received():
                return True
        return False

    @api.multi
    def test_moves_except(self):
        """PO is in exception at the delivery side if all the pickings are done or cancel, and order is not totally
        received."""
        if self.all_pickings_done_or_cancel():
            if not self.order_totally_received():
                return True
        return False


class PurchaseOrderLineJustInTime(models.Model):
    _inherit = 'purchase.order.line'
    _order = 'order_id, line_no, id'



    supplier_code = fields.Char(string="Supplier Code", compute='_compute_supplier_code')
    ack_ref = fields.Char("Acknowledge Reference", help="Reference of the supplier's last reply to confirm the delivery"
                                                        " at the planned date")
    date_ack = fields.Date("Last Acknowledge Date",
                           help="Last date at which the supplier confirmed the delivery at the planned date.")
    father_line_id = fields.Many2one('purchase.order.line', string="Very first line splited", readonly=True)
    children_line_ids = fields.One2many('purchase.order.line', 'father_line_id', string="Children lines")
    children_number = fields.Integer(string="Number of children", readonly=True, compute='_compute_children_number')

    @api.multi
    @api.depends('partner_id', 'product_id')
    def _compute_supplier_code(self):
        for rec in self:
            supplierinfo = self.env['product.supplierinfo']. \
                search([('id', 'in', rec.product_id.seller_ids.ids),
                        ('name', '=', rec.partner_id.id)], order='sequence, id', limit=1)
            if supplierinfo:
                rec.supplier_code = supplierinfo.product_code

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
        states_with_moves = self.env['purchase.order'].get_purchase_order_states_with_moves()
        states_confirmed = states_with_moves + ['confirmed']
        if result.order_id.state in states_confirmed:
            result.order_id.set_order_line_status('confirmed')
            if float_compare(result.product_qty, 0.0, precision_rounding=result.product_uom.rounding) != 0 and \
                    not result.move_ids and not self.env.context.get('no_update_moves') and \
                    result.order_id.state in states_with_moves:
                # We create associated moves
                self.env['purchase.order']._create_stock_moves(result.order_id, order_lines=result)
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
        done_moves = self.env['stock.move'].search([('purchase_line_id', '=', self.id),
                                                    ('state', '=', 'done')])
        done_moves_qty = sum([move.product_qty for move in done_moves])
        done_moves_qty_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                      done_moves_qty,
                                                                      self.product_uom.id)
        if self.product_id.type == 'service':
            target_qty = done_moves_qty_pol_uom
        running_moves = self.env['stock.move'].search([('purchase_line_id', '=', self.id),
                                                       ('state', 'not in', ['done', 'cancel'])])
        running_moves_qty = sum([move.product_qty for move in running_moves])
        running_moves_qty_pol_uom = self.env['product.uom']._compute_qty(self.product_id.uom_id.id,
                                                                         running_moves_qty,
                                                                         self.product_uom.id)
        if float_compare(target_qty, done_moves_qty_pol_uom, precision_rounding=self.product_uom.rounding) < 0:
            raise exceptions.except_orm(_(u"Error!"), _(u"Impossible to cancel moves at state done."))
        final_running_qty = target_qty - done_moves_qty_pol_uom
        moves_to_cancel = self.env['stock.move']
        if float_compare(running_moves_qty_pol_uom, final_running_qty,
                         precision_rounding=self.product_uom.rounding) > 0:
            moves_to_cancel = running_moves
            # If we cancel all the moves, the order may switch to 'picking_except' state.
            moves_to_cancel.write({'product_uom_qty': 0})
            running_moves_qty_pol_uom -= running_moves_qty_pol_uom
        if float_compare(running_moves_qty_pol_uom, final_running_qty,
                         precision_rounding=self.product_uom.rounding) < 0:
            self.order_id._create_stock_moves(self.order_id, order_lines=self)
        moves_to_cancel.action_cancel()

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
            raise exceptions.except_orm(_(u"Error!"), _(u"Impossible to cancel moves at state done."))
        if self.order_id.state in self.env['purchase.order'].get_purchase_order_states_with_moves():
            self.adjust_moves_qties(vals['product_qty'])

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
        if 'price_unit' in vals:
            for rec in self:
                active_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                              ('purchase_line_id', '=', rec.id),
                                                              ('state', 'not in', ['draft', 'cancel', 'done'])])
                active_moves.write({'price_unit': vals['price_unit']})
        return result

    @api.model
    def get_warehouse_for_stock_report(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)

    @api.multi
    def act_windows_view_graph(self):
        self.ensure_one()
        warehouse = self.get_warehouse_for_stock_report()
        if warehouse:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.levels.report',
                'name': _("Stock Evolution"),
                'view_type': 'form',
                'view_mode': 'graph,tree',
                'context': {'search_default_warehouse_id': warehouse.id,
                            'search_default_product_id': self.product_id.id}
            }
        else:
            raise exceptions.except_orm(_("Error!"), _("Your company does not have a warehouse"))

    @api.multi
    def unlink(self):
        procurements_to_detach = self.env['procurement.order'].search([('purchase_line_id', 'in', self.ids)])
        cancelled_procs = self.env['procurement.order'].search([('purchase_line_id', 'in', self.ids),
                                                                ('state', '=', 'cancel')])
        moves = self.env['stock.move'].search([('purchase_line_id', 'in', self.ids),
                                               ('state', 'not in', ['done', 'cancel'])])
        moves.action_cancel()
        result = super(PurchaseOrderLineJustInTime,
                       self.with_context(tracking_disable=True, message_code='delete_when_proc_no_exception')).unlink()
        # We reset initially cancelled procs to state 'cancel', because the unlink function of module purchase would
        # have set them to state 'exception'
        cancelled_procs.with_context(tracking_disable=True).write({'state': 'cancel'})
        procurements_to_detach.remove_procs_from_lines()
        return result
