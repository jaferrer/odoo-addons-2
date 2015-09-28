# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from datetime import *
from openerp.tests import common
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestInventorySpecific(common.TransactionCase):

    def setUp(self):
        super(TestInventorySpecific, self).setUp()

    def test_creation_inventaire_specific(self):
        company = self.browse_ref('base.main_company')
        location = self.browse_ref('stock.stock_location_stock')
        
        product_1=self.browse_ref('stock_specific_inventory.inv_product_test_product_1')
        product_2=self.browse_ref('stock_specific_inventory.inv_product_test_product_2')
        
        product_ids=[]
        product_ids.append(product_1.id)
        product_ids.append(product_2.id)
        
        
        inventory=self.env['stock.inventory'].create({
           'specify_product_ids': [(6,0,product_ids)],
           'location_id':location.id,
           'filter':'inventory_specific',
           'company_id':company.id,
           'name':'inventaire_init_1'
        })

        inventory.prepare_inventory()
        
        self.assertFalse(inventory.line_ids)
        
        #ajustement des articles product_1 et product_2
        
        self.env['stock.inventory.line'].create({
           'product_id': product_1.id,
           'product_qty':1000,
           'location_id':location.id,
           'inventory_id':inventory.id
        })
        inventory.action_done()
        
        
        inventory2=self.env['stock.inventory'].create({
           'specify_product_ids': [(6,0,product_ids)],
           'location_id':location.id,
           'filter':'inventory_specific',
           'company_id':company.id,
           'name':'inventaire_init_1'
        })
        
        self.assertTrue(inventory.line_ids)
        self.assertTrue(len(inventory.line_ids)==1)
        self.assertEqual(inventory.line_ids[0].product_id.name,'Test Product 1')
        