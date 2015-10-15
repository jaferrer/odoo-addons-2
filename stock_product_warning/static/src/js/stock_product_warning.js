openerp.stock_product_warning = function(instance){

    instance.stock.PickingEditorWidget.include({

        get_rows: function(){
            var model = this.getParent();
            var sorted_rows = this._super();
            _.each( sorted_rows, function(row){
                if (row.cols.product_id !== undefined){
                    row.cols.procurement_warning = _.findWhere(model.packoplines, {id: row.cols.id}).procurement_warning
                    row.cols.procurement_warning_msg = _.findWhere(model.packoplines, {id: row.cols.id}).procurement_warning_msg
                }
            });
            return sorted_rows;
        },
        
        renderElement: function(){
        	var self = this;
            this._super();
            //this.check_content_screen();
            this.$('.js_open_warning').click(function(){
            	var msg=_.findWhere(self.getParent().packoplines,{id:$(this).parents("[data-id]:first").data('id')}).procurement_warning_msg;
            	$("#js_open_warning_msg").html(msg);
                self.$el.siblings('#js_OpenStockWarning').modal();
            });
        }
      
    });
}
