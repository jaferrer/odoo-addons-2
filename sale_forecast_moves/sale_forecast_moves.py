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
from dateutil.relativedelta import relativedelta
from psycopg2 import OperationalError

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import fields, models, api, _, exceptions
import openerp


@job
def run_forecast_moves(session, model_name, ids):
    """Launch all schedulers"""
    compute_forecast_wizard = session.pool[model_name]
    compute_forecast_wizard._calculate_forecast_moves(session.cr, session.uid, ids, context=session.context)
    return "Scheduler ended sale forecast calculation."


class SaleForecastMovesWizard(models.TransientModel):
    _name = "sale.forecast.moves.wizard"

    forecast_weeks = fields.Integer("Number of weeks on which to make previsions")

    @api.multi
    def forecast_moves(self):
        session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
        run_forecast_moves.delay(session, 'sale.forecast.moves.wizard', self.ids)
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _calculate_forecast_moves(self, use_new_cursor=True):
        if use_new_cursor:
            cr = openerp.registry(self.env.cr.dbname).cursor()
            new_env = api.Environment(cr, self.env.user.id, self.env.context)
        else:
            new_env = self.env
        this = self.with_env(new_env)

        weeks = self.forecast_weeks
        if weeks < 0:
            raise exceptions.except_orm(_('Erreur!'), _("Veuillez choisir une autre valeur pour le nombre de semaines"))
        limit = fields.datetime.now()+relativedelta(days=-28)
        now = fields.datetime.now()

        produits = this.env['product.product'].search([('type', '=', 'product')])
        while produits:
            chunk_produits = produits[:100]
            produits = produits - chunk_produits
            for produit_id in chunk_produits:
                try:
                    list_of_moves = this.env['stock.move'].search(
                        [('state', '=', 'done'), ('location_id', '=', new_env.ref('stock.stock_location_stock').id),
                         ('product_id', '=', produit_id.id),
                         ('date', '>', limit.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                         ('prevision_move', '=', False)]
                    )

                    number_of_sales = sum([m.product_qty for m in list_of_moves]) / 4
                    if number_of_sales != 0:
                        for i in range(weeks):
                            date = now + relativedelta(weeks=+i)
                            move_of_week = this.env['stock.move'].search(
                                [('product_id', '=', produit_id.id), ('week', '=', (i + 1)),
                                 ('prevision_move', '=', True)]
                            )
                            if move_of_week:
                                move_of_week.write({
                                    'product_uom_qty': number_of_sales,
                                    'product_uom': produit_id.uom_id.id,
                                    'date': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'date_expected': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                })
                            else:
                                this.env['stock.move'].create({
                                    'name': "Mouvement de prevision pour la semaine n.%d" % (i+1),
                                    'product_id': produit_id.id,
                                    'product_uom_qty': number_of_sales,
                                    'product_uom': produit_id.uom_id.id,
                                    'date': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'date_expected': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'location_id': new_env.ref('stock.stock_location_stock').id,
                                    'location_dest_id': new_env.ref('stock.stock_location_customers').id,
                                    'prevision_move': True,
                                    'week': (i+1),
                                    'state': 'confirmed',
                                })
                    list_of_expired_moves = this.env['stock.move'].search(
                        [('product_id', '=', produit_id.id), ('prevision_move', '=', True), ('week', '>', weeks)]
                    )
                    list_of_expired_moves.write({'state': 'draft'})
                    list_of_expired_moves.unlink()
                except OperationalError:
                    if use_new_cursor:
                        produits = produits | chunk_produits
                        new_env.cr.rollback()
                        continue
                    else:
                        raise
            if use_new_cursor:
                new_env.cr.commit()
        if use_new_cursor:
            new_env.cr.commit()
            new_env.cr.close()
        return


class StockMoveExtended(models.Model):
    _inherit = "stock.move"

    prevision_move = fields.Boolean('Forecast Move')
    week = fields.Integer('Week')
