# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockChangeQuantValoStockQuant(models.Model):
    _inherit = 'stock.quant'

    cost_history_ids = fields.One2many('quant.cost.history', 'quant_id', string=u"Unit cost history")
    display_cost_history = fields.Boolean(string=u"Display unit cost history", compute='_compute_display_cost_history')

    @api.depends('cost_history_ids')
    @api.multi
    def _compute_display_cost_history(self):
        for rec in self:
            rec.display_cost_history = bool(rec.cost_history_ids)

    @api.model
    def check_access_rights_change_valo(self):
        group_stock_manager = self.env.ref('stock.group_stock_manager')
        if group_stock_manager not in self.env.user.groups_id:
            raise exceptions.except_orm(_("Error!"),
                                        _("You are not allowed to execute this action if you are not a stock manager."))

    @api.multi
    def change_quants_valorisation(self):
        self.check_access_rights_change_valo()
        products = set([quant.product_id for quant in self])
        if len(products) > 1:
            raise exceptions.except_orm(_("Error!"), _("You have quants of different products: %s. "
                                                       "Please change valorisations product by product") %
                                        ', '.join([product.display_name for product in products]))
        ctx = self.env.context.copy()
        ctx['default_quant_ids'] = [(6, 0, self.ids)]
        return {
            'name': _("Change quants valorisation"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.change.quant.valorisation',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def write(self, vals):
        cost = vals.get('cost')
        if vals.get('cost'):
            user_valorisation_id = self.env.context.get('user_valorisation', self.env.uid)
            for rec in self:
                if rec.cost != cost:
                    self.env['quant.cost.history'].create({
                        'quant_id': rec.id,
                        'date': fields.Datetime.now(),
                        'previous_cost': rec.cost,
                        'new_cost': cost,
                        'user_id': user_valorisation_id,
                    })
        return super(StockChangeQuantValoStockQuant, self).write(vals)


class StockChangeQuantValorisation(models.TransientModel):
    _name = 'stock.change.quant.valorisation'

    quant_ids = fields.Many2many('stock.quant', string=u"Quants", readonly=True, required=True)
    new_cost = fields.Float(string=u"New unit cost", required=True)

    @api.multi
    def change_quants_valorisation(self):
        self.ensure_one()
        self.quant_ids.with_context(user_valorisation=self.env.uid).sudo().write({'cost': self.new_cost})


class QuantCostHistory(models.Model):
    _name = 'quant.cost.history'

    quant_id = fields.Many2one('stock.quant', string=u"Quant", required=True)
    date = fields.Datetime(string=u"Date", required=True)
    previous_cost = fields.Float(string=u"Previous unit cost")
    new_cost = fields.Float(string=u"New unit cost")
    user_id = fields.Many2one('res.users', string=u"User", required=True)
