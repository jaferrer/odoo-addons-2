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

from openerp import models, fields, api, exceptions, _
from openerp.tools.float_utils import float_compare


class SplitLine(models.TransientModel):
    _name = 'split.line'
    _description = "Split Line"

    def _get_pol(self):
        return self.env['purchase.order.line'].browse(self.env.context.get('active_id'))

    line_id = fields.Many2one('purchase.order.line', string="Direct parent line in purchase order", default=_get_pol,
                              required=True, readonly=True)
    qty = fields.Float(string="New quantity of direct parent line")

    @api.multi
    def _check_split_possible(self, done_procs_qty):

        """
        Raises error if it is impossible to split the purchase order line.
        """

        prec = self.line_id.product_uom.rounding

        self.ensure_one()
        if self.env.context.get('active_ids') and len(self.env.context.get('active_ids')) > 1:
            raise exceptions.except_orm(_('Error!'), _("Please split lines one by one"))
        else:
            if float_compare(self.qty, 0, precision_rounding=prec) <= 0:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split a negative or null quantity"))
            if self.line_id.state not in ['draft', 'confirmed']:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split line which is not in state draft or "
                                                           "confirmed"))
            if self.line_id.state == 'draft':
                if float_compare(self.qty, self.line_id.product_qty, precision_rounding=prec) >= 0:
                    raise exceptions.except_orm(_('Error!'), _("Please choose a lower quantity to split"))
        if float_compare(self.qty, done_procs_qty, precision_rounding=prec) < 0:
            raise exceptions.except_orm(_('Error!'), _("Please choose a lower quantity to split"))
        if self.line_id.state == 'confirmed':
            _sum = sum([x.product_qty for x in self.line_id.move_ids if x.state == 'done'])
            _sum_pol_uom = self.env['product.uom']._compute_qty(self.line_id.product_id.uom_id.id, _sum,
                                                                self.line_id.product_uom.id)
            if self.qty < _sum_pol_uom:
                raise exceptions.except_orm(_('Error!'), _("Impossible to split a move in state done"))
            not_cancelled_qty = sum([m.product_qty for m in self.line_id.move_ids if m.state != 'cancel'])
            not_cancelled_qty_pol_uom = self.env['product.uom']._compute_qty(self.line_id.product_id.uom_id.id,
                                                                             not_cancelled_qty,
                                                                             self.line_id.product_uom.id)
            if self.qty >= not_cancelled_qty_pol_uom:
                raise exceptions.except_orm(_('Error!'), _("Please choose a lower quantity to split"))

    @api.multi
    def do_split(self):
        """
        Separates a purchase order line into two ones.
        """

        original_qty = self.line_id.product_qty
        new_pol_qty = original_qty - self.qty
        done_procs = self.env['procurement.order'].search([('id', 'in', self.line_id.procurement_ids.ids),
                                                           ('state', '=', 'done')])
        running_procs = self.env['procurement.order'].search([('id', 'in', self.line_id.procurement_ids.ids),
                                                              ('state', 'not in', ['done', 'cancel'])])
        done_procs_qty = sum([self.env['product.uom']._compute_qty(proc.product_uom.id,
                                                                   proc.product_qty,
                                                                   self.line_id.product_uom.id)
                              for proc in done_procs])
        running_procs_qty = sum([self.env['product.uom']._compute_qty(proc.product_uom.id,
                                                                      proc.product_qty,
                                                                      self.line_id.product_uom.id)
                                 for proc in running_procs])
        self._check_split_possible(done_procs_qty)
        prec = self.line_id.product_uom.rounding
        while running_procs and float_compare(done_procs_qty + running_procs_qty, self.qty,
                                              precision_rounding=prec) > 0:
            procurement_to_detach = running_procs[0]
            qty_to_detach_pol_uom = self.env['product.uom']._compute_qty(procurement_to_detach.product_uom.id,
                                                                         procurement_to_detach.product_qty,
                                                                         self.line_id.product_uom.id)
            procurement_to_detach.remove_procs_from_lines(unlink_moves_to_procs=True)
            running_procs_qty -= qty_to_detach_pol_uom
        self.line_id.with_context().write({'product_qty': self.qty})

        # Get a line_no for the new purchase.order.line
        father_line_id = self.line_id.father_line_id or self.line_id
        orig_line_no = father_line_id.line_no or "0"
        new_line_no = orig_line_no + ' - ' + str(father_line_id.children_number + 1)

        # Create new purchase.order.line
        new_line = self.line_id.with_context().copy({
            'product_qty': new_pol_qty,
            'move_ids': False,
            'children_line_ids': False,
            'line_no': new_line_no,
            'father_line_id': father_line_id.id,
        })
        self.line_id.adjust_moves_qties(self.line_id.product_qty)
        new_line.adjust_moves_qties(new_line.product_qty)


class LaunchPurchasePlanner(models.TransientModel):
    _name = 'launch.purchase.planner'

    compute_all = fields.Boolean(string="Compute all the products", default=True)
    product_ids = fields.Many2many('product.product', string="Products")
    supplier_ids = fields.Many2many('res.partner', string="Suppliers", domain=[('supplier', '=', True)])

    @api.multi
    def procure_calculation(self):
        self.env['procurement.order'].purchase_schedule(compute_product_ids=self.product_ids,
                                                        compute_supplier_ids=self.supplier_ids,
                                                        compute_all_products=self.compute_all,
                                                        jobify=True, manual=True)
