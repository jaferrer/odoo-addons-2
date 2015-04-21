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
from openerp import fields, models, api
import openerp

# modèle des mouvements de stock: stock.move
# 0. Créer un pop-up pour entrer le nombre de semaines sur lequel mettre des prévisions.
# - Créer un modèle de type model.TransientModel => ça crée un modèle non persistent
# - Dans ce modèle mettre un champ Integer pour récupérer le nombre de semaines
# - Créer une vue pour ce pop-up (sans oublier le bouton de validation => type=object, name=le_nom_de_la_fonction
# => La fonction de calcul est dans la classe du pop-up
# - Créer l'action de fenêtre pour le pop-up avec 'target = new' (voir la doc dans tutorial/building a module/wizard
# - Créer un menu pour ouvrir l'action de fenêtre
# 1. Déterminer le nombre de ventes par semaine: additionner les mouvements de stock de sortie sur les 28 derniers jours
# sur l'article concerné et diviser par 4
# => Utiliser la fonction search
# => liste_de_moves = self.env['stock.move'].search([('date','<',blabla),('product_id','=',produit_id.id),('state','=','done')])
# 2. Créer un mouvement par semaine sur une durée définie par l'utilisateur (pop-up à créer)
# => self.env['stock.move'].create({'product_id': produit_id.id, 'product_uom_qty': 3, })
#
# 3. Créer une fonction qui supprimer les mouvements de prévision lorsqu'ils sont dans le passé
#
# Exemple: odoo/addons/stock/wizard => orderpoint_procurement (Le pop-up qui s'ouvre lorsqu'on clique sur
# "Entrepot/Schedulers/Compute minimum stock rules only"


@job
def run_forecast_moves(session, model_name, ids):
    """Launch all schedulers"""
    compute_forecast_wizard = session.pool[model_name]
    compute_forecast_wizard._calculate_forecast_moves(session.cr, session.uid, ids, context=session.context)
    return "Scheduler ended sale forecast calculation."


class sale_forecast_moves_wizard(models.TransientModel):
    _name = "sale.forecast.moves.wizard"

    forecast_weeks = fields.Integer("Number of weeks on which to make previsions")

    @api.multi
    def forecast_moves(self):
        session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
        job_uuid = run_forecast_moves.delay(session, 'sale.forecast.moves.wizard', self.ids)
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
        LIMIT = fields.datetime.now()+relativedelta(days=-28)
        NOW = fields.datetime.now()

        produits = this.env['product.product'].search([('type','=','product')])
        while produits:
            chunk_produits = produits[:100]
            produits = produits - chunk_produits
            for produit_id in chunk_produits:
                try:
                    list_of_moves = this.env['stock.move'].search([('state','=','done'),
                                                            ('location_id','=',new_env.ref('stock.stock_location_stock').id),
                                                            ('product_id','=',produit_id.id),
                                                            ('date','>',LIMIT.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                            ('prevision_move','=',False)])

                    number_of_sales = sum([m.product_qty for m in list_of_moves]) / 4
                    if number_of_sales != 0:
                        for i in range(weeks):
                            DATE = NOW+relativedelta(weeks=+i)
                            move_of_week = this.env['stock.move'].search([('product_id','=',produit_id.id),
                                                            ('week','=',(i+1)),
                                                            ('prevision_move','=',True)])
                            if move_of_week:
                                move_of_week.write({
                                    'product_uom_qty': number_of_sales,
                                    'product_uom': produit_id.uom_id.id,
                                    'date': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'date_expected': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                })
                            else:
                                this.env['stock.move'].create({
                                'name': "Mouvement de prevision pour la semaine n.%d" % (i+1),
                                #'invoice_control': 'none',
                                'product_id': produit_id.id,
                                'product_uom_qty': number_of_sales,
                                'product_uom': produit_id.uom_id.id,
                                'date': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'date_expected': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'location_id': new_env.ref('stock.stock_location_stock').id,
                                'location_dest_id': new_env.ref('stock.stock_location_customers').id,
                                'prevision_move': True,
                                'week': (i+1),
                                })
                    list_of_expired_moves = this.env['stock.move'].search([('product_id','=',produit_id.id),
                                                                            ('prevision_move','=',True),
                                                                            ('week','>',weeks)])
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


class stock_move_etendu(models.Model):
    _inherit = "stock.move"

    prevision_move = fields.Boolean('Mouvement de prevision')
    week = fields.Integer('week')
