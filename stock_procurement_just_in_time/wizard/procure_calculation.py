#
#   Copyright (C) 2008-2015 by 
#     Nicolas Piganeau <npi@m4x.org> & TS2 Team                                                           
#                                                                         
#   This program is free software; you can redistribute it and/or modify  
#   it under the terms of the GNU General Public License as published by  
#   the Free Software Foundation; either version 2 of the License, or     
#   (at your option) any later version.                                   
#                                                                         
#   This program is distributed in the hope that it will be useful,       
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
#   GNU General Public License for more details.                          
#                                                                         
#   You should have received a copy of the GNU General Public License     
#   along with this program; if not, write to the                         
#   Free Software Foundation, Inc.,                                       
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             
#

from openerp import fields, models, api


class StockComputeAll(models.TransientModel):
    _inherit = 'procurement.order.compute.all'

    compute_all = fields.Boolean(string=u"Compute all the products", default=True)
    product_ids = fields.Many2many('product.product', string=u"Products to compute")

    @api.multi
    def procure_calculation(self):
        return super(StockComputeAll, self.with_context(compute_product_ids=self.product_ids.ids,
                                                        compute_all_products=self.compute_all)).procure_calculation()
