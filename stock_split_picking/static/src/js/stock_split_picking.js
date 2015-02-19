openerp.stock_split_picking = function(instance){

    instance.stock.PickingEditorWidget.include({
        renderElement: function(){
            var self = this;
            this._super();
            this.$('.js_pick_split').click(function(){ self.getParent().split_picking(); });
        },
        check_content_screen: function(){
            //get all visible element and if none has positive qty, disable put in pack and process button
            var self = this;
            var processed = this.$('.js_pack_op_line.processed');
            var qties = this.$('.js_pack_op_line:not(.processed):not(.hidden) .js_qty').map(function(){return $(this).val()});
            var disabled = true;
            $.each(qties,function(index, value){
                if (parseInt(value)>0){
                    disabled = false;
                }
            });
            if (disabled){
                if (processed.length === 0){
                    self.$('.js_pick_split').addClass('disabled');
                }
                else {
                    self.$('.js_pick_split').removeClass('disabled');
                }
            }
            else{
                self.$('.js_pick_split').removeClass('disabled');
            }
            return this._super();
        },

    })

    instance.stock.PickingMainWidget.include({
        split_picking: function(){
            console.log("Hey, I split !")
            var self = this;
            return new instance.web.Model('stock.picking')
                .call('action_split_from_ui',[self.picking.id, {'default_picking_type_id': self.picking_type_id}])
                .then(function(){
                    return self.refresh_ui(self.picking.id);
                });
        },
    })

}