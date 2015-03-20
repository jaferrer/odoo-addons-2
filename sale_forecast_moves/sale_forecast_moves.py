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

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

from openerp import fields, models, api

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

class sale_forecast_moves_wizard(models.TransientModel):
    _name = "sale.forecast.moves.wizard"

    forecast_weeks = fields.Integer("Number of weeks on which to make previsions")

    @api.multi
    def forecast_moves(self):

        LIMIT = fields.datetime.now()+relativedelta(days=-28)
        NOW = fields.datetime.now()

        for produit_id in self.env['product.product'].search([('type','=','product')]):
            list_of_moves = self.env['stock.move'].search([('state','=','done'),
                                                    ('location_id','=',self.env.ref('stock.stock_location_stock').id),
                                                    ('product_id','=',produit_id.id),
                                                    ('date','>',LIMIT.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                    ('prevision_move','=',False)])


            number_of_sales = sum([m.product_qty for m in list_of_moves]) / 4



            if number_of_sales != 0:
                for i in range(self.forecast_weeks):

                    DATE = NOW+relativedelta(weeks=+i)

                    move_of_week = self.env['stock.move'].search([('product_id','=',produit_id.id),
                                                    ('name','=','Mouvement de prevision pour la semaine n.%d' % (i+1)),
                                                    ('prevision_move','=',True)])

                    if move_of_week:
                        move_of_week.product_uom_qty = number_of_sales
                        move_of_week.product_uom = produit_id.uom_id.id
                        move_of_week.date = DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        move_of_week.date_expected = DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                    else:
                        self.env['stock.move'].create({
                        'name': "Mouvement de prevision pour la semaine n.%d" % (i+1),
                        'invoice_control': 'none',
                        'product_id': produit_id.id,
                        'product_uom_qty': number_of_sales,
                        'product_uom': produit_id.uom_id.id,
                        'date': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'date_expected': DATE.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                        'prevision_move': True,
                        'ID': (i+1),
                        })

            list_of_expired_moves = self.env['stock.move'].search([('product_id','=',produit_id.id),
                                                                    ('prevision_move','=',True),
                                                                    ('ID','>',self.forecast_weeks)])

            list_of_expired_moves.unlink()



        return {'type': 'ir.actions.act_window_close'}


class stock_move_etendu(models.Model):
    _inherit = "stock.move"

    prevision_move = fields.Boolean('Mouvement de prevision')
    ID = fields.Integer('ID')