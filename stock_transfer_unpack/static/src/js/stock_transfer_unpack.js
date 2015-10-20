openerp.stock_transfer_unpack = function(instance){

	instance.stock.PickingEditorWidget.include({

        get_rows: function(){
            var model = this.getParent();
            var sorted_rows = this._super();
            _.each( this.rows, function(row){
                if (row.cols.product_id !== undefined){
                    row.cols.is_package = false;
                } else {
                	row.cols.is_package = true;
                }
            });
            return sorted_rows;
        },
        
        renderElement: function(){
        	var self = this;
            this._super();
            this.check_content_screen();
            this.$('.js_unpack_select').click(function(){
                var op_id = $(this).parents("[data-id]:first").data('id');
                self.getParent().unpack_select(op_id);
            });
        },
    
	    
      
    });
	
	instance.stock.PickingMainWidget.include({
		unpack_select: function(op_id){
	        var self = this;
	        return new instance.web.Model('stock.pack.operation')
	            .call('unpack',[parseInt(op_id)])
	            .then(function(){
	                return self.refresh_ui(self.picking.id);
	            });
	    }
    })
}
