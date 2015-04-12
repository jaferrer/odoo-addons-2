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

from openerp.tests import common

from dateutil.relativedelta import relativedelta

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from openerp import fields

class TestSaleForecast(common.TransactionCase):

    def setUp(self):
        super(TestSaleForecast, self).setUp()

    def test_10_forecast_sales(self):
        """Test des prévisions de vente."""
        # 1. Créer des jeux de mouvements représentant des ventes passées (démo ou directement avec un create)
        # 2. Sur le cahier tu calcules combien de prévision il doit te mettre
        # 3. Tu lances la fonction forecast_move avec une valeur de forecast_weeks
        # 4. Tu fais des requetes pour aller chercher les mouvements de prévision qui devraient être créés par la fonction
        # 5. Tu vérifier que tu as le bon nombre de mouvements de prévision
        # 6. Tu itères sur ces mouvements de prévision pour vérifier que les dates et les qté sont bonnes
        #move1 = self.ref('product.product_product_6') # Renvoie un ID tout seul, donc ne pas mettre .id après !
        #self.browse_ref('product.product_product_6') # Renvoie un enregistrement => mettre .id si besoin.
        #mouvement1 = self.browse_ref('sale_forecast_moves.mouvement_1')
        # Attention de prendre des références que l'on va avoir dans la base

        DATE1 = fields.datetime.now()+relativedelta(days=-27)
        NOW = fields.datetime.now()


        move1 = self.env['stock.move'].create({
                        'name': "Mouvement de test vente x ",
                        'product_id': self.ref('sale_forecast_moves.produit_de_test'),
                        'product_uom_qty': 28,
                        'product_uom': self.ref('product.product_uom_unit'),
                        'date': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'date_expected': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                        'prevision_move': False,
                        'state': 'done',
        })

        move2 = self.env['stock.move'].create({
                        'name': "Mouvement de test vente y ",
                        'product_id': self.ref('sale_forecast_moves.produit_de_test'),
                        'product_uom_qty': 45,
                        'product_uom': self.ref('product.product_uom_unit'),
                        'date': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'date_expected': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                        'prevision_move': False,
                        'state': 'done',
        })

        move3 = self.env['stock.move'].create({
                        'name': "Mouvement de test vente z ",
                        'product_id': self.ref('sale_forecast_moves.produit_de_test'),
                        'product_uom_qty': 14,
                        'product_uom': self.ref('product.product_uom_unit'),
                        'date': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'date_expected': DATE1.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                        'prevision_move': False,
                        'state': 'done',
        })

        popup1 = self.env['sale.forecast.moves.wizard'].create({
            'forecast_weeks': 4,
        })
        popup1.forecast_moves()

        prev_moves = self.env['stock.move'].search([('prevision_move','=',True),
                                                    ('product_id','=',self.ref('sale_forecast_moves.produit_de_test'))])

        self.assertEqual(len(prev_moves), 4)


        for i in range(len(prev_moves)):

            DATE2 = NOW+relativedelta(weeks=+i)

            pmove = self.env['stock.move'].search([('prevision_move','=',True),
                                                   ('product_id','=',self.ref('sale_forecast_moves.produit_de_test')),
                                                   ('week','=',(i+1))])

            self.assertTrue(pmove)
            self.assertEqual(pmove.product_uom_qty, 21.75)
            self.assertEqual(pmove.date[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])
            self.assertEqual(pmove.date_expected[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])




        popup2 = self.env['sale.forecast.moves.wizard'].create({
            'forecast_weeks': 2,
        })
        popup2.forecast_moves()

        prev_moves = self.env['stock.move'].search([('prevision_move','=',True),
                                                    ('product_id','=',self.ref('sale_forecast_moves.produit_de_test'))])

        self.assertEqual(len(prev_moves), 2)


        for i in range(4):

            DATE2 = NOW+relativedelta(weeks=+i)

            pmove = self.env['stock.move'].search([('prevision_move','=',True),
                                                   ('product_id','=',self.ref('sale_forecast_moves.produit_de_test')),
                                                   ('week','=',(i+1))])
            if i < 2:
                self.assertTrue(pmove)
                self.assertEqual(pmove.product_uom_qty, 21.75)
                self.assertEqual(pmove.date[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])
                self.assertEqual(pmove.date_expected[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])


            else:
                self.assertFalse(pmove)




        popup3 = self.env['sale.forecast.moves.wizard'].create({
            'forecast_weeks': 5,
        })
        popup3.forecast_moves()

        prev_moves = self.env['stock.move'].search([('prevision_move','=',True),
                                                    ('product_id','=',self.ref('sale_forecast_moves.produit_de_test'))])

        self.assertEqual(len(prev_moves), 5)


        for i in range(len(prev_moves)):

            DATE2 = NOW+relativedelta(weeks=+i)

            pmove = self.env['stock.move'].search([('prevision_move','=',True),
                                                   ('product_id','=',self.ref('sale_forecast_moves.produit_de_test')),
                                                   ('week','=',(i+1))])

            self.assertTrue(pmove)
            self.assertEqual(pmove.product_uom_qty, 21.75)
            self.assertEqual(pmove.date[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])
            self.assertEqual(pmove.date_expected[:10], DATE2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)[:10])



        popup4 = self.env['sale.forecast.moves.wizard'].create({
            'forecast_weeks': 0,
        })
        popup4.forecast_moves()

        prev_moves = self.env['stock.move'].search([('prevision_move','=',True),
                                                    ('product_id','=',self.ref('sale_forecast_moves.produit_de_test'))])

        self.assertEqual(len(prev_moves), 0)


        for i in range(5):

            pmove = self.env['stock.move'].search([('prevision_move','=',True),
                                                   ('product_id','=',self.ref('sale_forecast_moves.produit_de_test')),
                                                   ('week','=',(i+1))])

            self.assertFalse(pmove)

