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

from openerp import models, fields, api


class BillOfSpecifications(models.Model):
    _name = 'bill.of.specifications'
    _inherit = 'mail.thread'

    name = fields.Char(string="Name")
    validation_date = fields.Datetime(string="Validation date")
    bos_line_ids = fields.One2many('bill.of.specifications.line', 'bos_id', string="Direct lines of specification",
                                   help="Countains only direct children lines")
    amount_total = fields.Float(string="Amount total", compute='_compute_amount_total', store=True,
                                track_visibility='onchange')

    @api.depends('bos_line_ids', 'bos_line_ids.cost')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum([l.cost for l in rec.bos_line_ids])


class BillOfSpecificationsLine(models.Model):
    _name = 'bill.of.specifications.line'

    cost = fields.Float(string="Cost", help="Do not specify cost if the line has children")
    template_line = fields.Boolean(string="Can be reused in another project")
    name = fields.Char(string="Short description")
    description = fields.Text(string="Full description")
    bos_id = fields.Many2one('bill.of.specifications', string="Bill of specifications",
                             help="Only direct parent bill of specifications")
    parent_line_id = fields.Many2one('bill.of.specifications.line', string="Direct parent line")
    children_line_ids = fields.One2many('bill.of.specifications.line', 'parent_line_id',
                                        string="Direct children lines")
    amount_subtotal = fields.Float(string="Amount subtotal", compute='_compute_amount_subtotal')
    sequence = fields.Integer(string="Sequence")

    @api.multi
    def _compute_amount_subtotal(self):
        for rec in self:
            if rec.children_line_ids:
                rec.amount_subtotal = sum([l.amount_subtotal for l in rec.children_line_ids])
            else:
                rec.amount_subtotal = rec.cost
            print '_compute_amount_subtotal', rec.amount_subtotal
