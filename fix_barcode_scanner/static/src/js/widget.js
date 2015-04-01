openerp.fix_barcode_scanner = function(instance) {

    instance.stock.BarcodeScanner.include({
        connect: function(callback){
            var code = "";
            var timeStamp = 0;
            var timeout = null;

            this.handler = function(e){
                if(e.which === 13){
                    if(code.length >= 3){
                        callback(code);
                    }
                    code = "";
                    return;
                }
                code += String.fromCharCode(e.which);
            };

            $('body').on('keypress', this.handler);

        },
    });

    instance.stock.PickingMainWidget.include({
        // load the picking data from the server. If picking_id is undefined, it will take the first picking
        // belonging to the category
        load: function(picking_id){
            var self = this;

            function load_picking_list(type_id){
                var pickings = new $.Deferred();
                new instance.web.Model('stock.picking')
                    .call('get_next_picking_for_ui',[{'default_picking_type_id':parseInt(type_id)}])
                    .then(function(picking_ids){
                        if(!picking_ids || picking_ids.length === 0){
                            (new instance.web.Dialog(self,{
                                title: _t('No Picking Available'),
                                buttons: [{
                                    text:_t('Ok'),
                                    click: function(){
                                        self.menu();
                                    }
                                }]
                            }, _t('<p>We could not find a picking to display.</p>'))).open();

                            pickings.reject();
                        }else{
                            self.pickings = picking_ids;
                            pickings.resolve(picking_ids);
                        }
                    });

                return pickings;
            }

            // if we have a specified picking id, we load that one, and we load the picking of the same type as the active list
            if( picking_id ){
                var loaded_picking = new instance.web.Model('stock.picking')
                    .call('read',[[parseInt(picking_id)], [], new instance.web.CompoundContext()])
                    .then(function(picking){
                        self.picking = picking[0];
                        self.picking_type_id = picking[0].picking_type_id[0];
                        return load_picking_list(self.picking.picking_type_id[0]);
                    });
            }else{
                // if we don't have a specified picking id, we load the pickings belong to the specified type, and then we take
                // the first one of that list as the active picking
                var loaded_picking = new $.Deferred();
                load_picking_list(self.picking_type_id)
                    .then(function(){
                        return new instance.web.Model('stock.picking').call('read',[self.pickings[0],[], new instance.web.CompoundContext()]);
                    })
                    .then(function(picking){
                        self.picking = picking;
                        self.picking_type_id = picking.picking_type_id[0];
                        loaded_picking.resolve();
                    });
            }

            return loaded_picking.then(function(){
                    if (self.locations.length === 0) {
                        return new instance.web.Model('stock.location').call('search',[[['usage','=','internal']]]).then(function(locations_ids){
                            return new instance.web.Model('stock.location').call('read',[locations_ids, []]).then(function(locations){
                                self.locations = locations;
                            });
                        });
                    }
                }).then(function(){
                    return new instance.web.Model('stock.picking').call('check_group_pack').then(function(result){
                        return self.show_pack = result;
                    });
                }).then(function(){
                    return new instance.web.Model('stock.picking').call('check_group_lot').then(function(result){
                        return self.show_lot = result;
                    });
                }).then(function(){
                    if (self.picking.pack_operation_exist === false){
                        self.picking.recompute_pack_op = false;
                        return new instance.web.Model('stock.picking').call('do_prepare_partial',[[self.picking.id]]);
                    }
                }).then(function(){
                        return new instance.web.Model('stock.pack.operation').call('search',[[['picking_id','=',self.picking.id]]])
                }).then(function(pack_op_ids){
                        return new instance.web.Model('stock.pack.operation').call('read',[pack_op_ids, [], new instance.web.CompoundContext()])
                }).then(function(operations){
                    self.packoplines = operations;
                    var package_ids = [];

                    for(var i = 0; i < operations.length; i++){
                        if(!_.contains(package_ids,operations[i].result_package_id[0])){
                            if (operations[i].result_package_id[0]){
                                package_ids.push(operations[i].result_package_id[0]);
                            }
                        }
                    }
                    return new instance.web.Model('stock.quant.package').call('read',[package_ids, [], new instance.web.CompoundContext()])
                }).then(function(packages){
                    self.packages = packages;
                }).then(function(){
                        return new instance.web.Model('product.ul').call('search',[[]])
                }).then(function(uls_ids){
                        return new instance.web.Model('product.ul').call('read',[uls_ids, []])
                }).then(function(uls){
                    self.uls = uls;
                });
        },
    });
}