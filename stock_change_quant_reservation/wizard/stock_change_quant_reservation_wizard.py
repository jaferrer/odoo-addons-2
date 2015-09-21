'''
Created on 15 sept. 2015

@author: asalaun
'''

from openerp import models, fields, api

class StockChangeQuantPicking(models.TransientModel):
    _name = 'stock.quant.picking'
    
    @api.model
    def _picking_list_get(self):
        quants_ids = self.env.context.get('active_ids', [])
        if not quants_ids:
            return []
        quants = self.env['stock.quant'].browse(quants_ids)
        items=[]
        for quant in quants:
            if not quant.package_id:
                compare=items
                moves=self.env['stock.move'].search(['&',('product_id','=',quant.product_id.id),('state','not in',['done','cancel']),('|',('reserved_quant_ids','=',False),(quant.id,'not in','reserved_quant_ids'))])
                sublist=[]
                for move in moves:
                    sublist.append(move.picking_id.id)
                if compare:
                    items=set(compare).intersection(set(sublist))
                else:
                    items=sublist
       
        return [('id','in',items)]
    
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Pickings',domain=_picking_list_get,required=True)
    
    @api.one
    def do_apply(self):
        moves=self.picking_id.move_lines
        quants_ids = self.env.context.get('active_ids', [])
        quants = self.env['stock.quant'].browse(quants_ids)
        for quant in quants:
            for move in moves:
                if(move.product_id.id==quant.product_id.id):
                    move.action_confirm()
                    quant.quants_reserve([(quant, move.product_uom_qty)], move)
                    break
            
        self.picking_id.do_prepare_partial()
        return True
