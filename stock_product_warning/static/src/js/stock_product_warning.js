openerp.stock_product_warning = function(instance){

    instance.stock.PickingEditorWidget.include({

        get_rows: function(){
            var model = this.getParent();
            var sorted_rows = this._super();
            _.each( this.rows, function(row){
                if (row.cols.product_id !== undefined){
                    row.cols.procurement_warning = _.findWhere(model.packoplines, {id: row.cols.id}).procurement_warning
                }
            });
            return sorted_rows;
        },
    });
}
