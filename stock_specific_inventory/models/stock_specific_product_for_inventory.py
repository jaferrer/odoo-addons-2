from openerp import fields, models, api
from openerp.tools.sql import drop_view_if_exists

class StockInventorySpecific(models.Model):
    _inherit = 'stock.inventory'   

    def _get_available_filters(self):
        """
           This function will return the list of filter allowed according to the options checked
           in 'Settings\Warehouse'.

           :rtype: list of tuple
        """
        #default available choices
        res_filter = super(StockInventorySpecific,self)._get_available_filters()
        res_filter.append(('inventory_specific', 'Selected products'))
        return res_filter
    
    filter = fields.Selection(selection=_get_available_filters)
    specify_product_ids = fields.Many2many("product.product", string="Products Specifics")
    
    @api.model
    def _get_inventory_lines(self, inventory):
        
        vals=[]
        if inventory.filter == 'inventory_specific':
            location_obj = self.env['stock.location']
            product_obj = self.env['product.product']
            location_ids = location_obj.search([('id', 'child_of', [inventory.location_id.id])])
            domain = ' location_id in %s'
            args = (tuple(location_ids.ids),)
            if inventory.partner_id:
                domain += ' and owner_id = %s'
                args += (inventory.partner_id.id,)
            if inventory.lot_id:
                domain += ' and lot_id = %s'
                args += (inventory.lot_id.id,)
            if inventory.specify_product_ids:
                domain += ' and product_id in %s'
                args += (tuple(inventory.specify_product_ids.ids),)
            if inventory.package_id:
                domain += ' and package_id = %s'
                args += (inventory.package_id.id,)
    
            self.env.cr.execute('''
               SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
               FROM stock_quant WHERE''' + domain + '''
               GROUP BY product_id, location_id, lot_id, package_id, partner_id
            ''', args)

            for product_line in self.env.cr.dictfetchall():
                #replace the None the dictionary by False, because falsy values are tested later on
                for key, value in product_line.items():
                    if not value:
                        product_line[key] = False
                product_line['inventory_id'] = inventory.id
                product_line['theoretical_qty'] = product_line['product_qty']
                if product_line['product_id']:
                    product = product_obj.browse(product_line['product_id'])
                    product_line['product_uom_id'] = product.uom_id.id
                vals.append(product_line)
        else:
            vals=super(StockInventorySpecific,self)._get_inventory_lines(inventory)
        return vals
    

class StockSpecificProductInventory(models.Model):
    _name = 'stock.specific.product.inventory'
    _auto = False

    stock_warehouse_id = fields.Many2one('stock.warehouse', readonly=True, index=True,string='Entrepot')
    product_id = fields.Many2one('product.product', readonly=True, index=True,string='Article')
    qty = fields.Integer('total',readonly=True)
    invetory_date = fields.Datetime('Date du dernier inventaire',readonly=True)
    move_stock_date = fields.Datetime('Date du dernier mouvement de stock',readonly=True)

    def init(self, cr):
        drop_view_if_exists(cr, "stock_specific_product_inventory")
        cr.execute("""
        create or replace view stock_specific_product_inventory as (
            with recursive top_parent(loc_id, top_parent_id) as (
                    select
                        sl.id as loc_id, sl.id as top_parent_id
                    from
                        stock_location sl
                        left join stock_location slp on sl.location_id = slp.id
                    where
                        sl.usage='internal'
                union
                    select
                        sl.id as loc_id, tp.top_parent_id
                    from
                        stock_location sl, top_parent tp
                    where
                        sl.usage='internal' and sl.location_id=tp.loc_id
            )
select stock_warehouse.id::text||'-'||product_product.id::text as id,stock_warehouse.id as stock_warehouse_id,product_product.id as product_id,sum(stock_quant.qty) as qty,max(stock_inventory.date) as invetory_date,max(stock_move.date) as move_stock_date from stock_warehouse
inner join top_parent on stock_warehouse.lot_stock_id=top_parent.top_parent_id
inner join stock_quant on stock_quant.location_id=top_parent.loc_id
inner join product_product on product_product.id=stock_quant.product_id
left join (select location_id,max(date) as date from stock_inventory s
group by location_id) stock_inventory on stock_inventory.location_id=top_parent.loc_id
left join (select location_id,product_id,max(date) as date from stock_move m
group by location_id,product_id) stock_move on stock_move.location_id=top_parent.loc_id and stock_move.product_id=product_product.id
group by stock_warehouse.id,product_product.id)
        """)
    
    @api.model
    def create_inventory(self):
        product_view_ids = self.env.context.get('active_ids', [])
        if not product_view_ids:
            return []
        product_views = self.env['stock.specific.product.inventory'].browse(product_view_ids)
        
        for entrepot in self.env['stock.warehouse'].search([]):
            products = product_views.filtered(lambda x: x.stock_warehouse_id == entrepot).mapped(lambda x:x.product_id)
            if products:
                self.env['stock.inventory'] .create({ 
                                                   'specify_product_ids': [(6,0,products.ids)],
                                                   'location_id':entrepot.lot_stock_id.id,
                                                   'filter':'inventory_specific',
                                                   'company_id':entrepot.company_id.id,
                                                   'name':'inventaire'+'-'+entrepot.name+'-'+fields.Datetime.now()
                                                   }
                                                  )
        
        return {
            'name': 'Inventory Adjustments',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.inventory',
            'type': 'ir.actions.act_window'
        }