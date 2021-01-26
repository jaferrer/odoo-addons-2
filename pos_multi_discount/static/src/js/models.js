odoo.define('pos_multi_discount.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var gui = require('point_of_sale.gui');
    var chrome = require('point_of_sale.chrome');
    var screens = require('point_of_sale.screens');
    var field_utils = require('web.field_utils');

    models.load_fields("product.product", ["discount_pc"]);

    var DiscountButton = screens.ActionButtonWidget.extend({
        template: 'DiscountButton',
        button_click: function(options){
            options = options || {};
            var self = this;
            var def  = new $.Deferred();

            var list = [];
            for (var i = 0; i < this.pos.config.discount_product_ids.length; i++) {
                var product = this.pos.db.get_product_by_id(this.pos.config.discount_product_ids[i]);
                list.push({
                     'label': product.display_name,
                     'item':  product,
                 });

            }

            this.gui.show_popup('selection',{
                title: options.title || _t('Remise'),
                list: list,
                confirm: function(product){ def.resolve(product); },
                cancel: function(){ def.reject(); },
            });

            return def.then(function(product){
                self.gui.show_popup('number',{
                    'title': _t('Pourcentage de remise'),
                    'value': product.discount_pc,
                    'confirm': function(val) {
                        val = Math.round(Math.max(0,Math.min(100,field_utils.parse.float(val))));
                        self.apply_discount(val, product.id);
                    },
                });
            });
        },

        apply_discount: function(pc, id) {
            var order    = this.pos.get_order();
            var lines    = order.get_orderlines();
            var product  = this.pos.db.get_product_by_id(id);
            if (product === undefined) {
                this.gui.show_popup('error', {
                    title : _t("Aucune remise trouvée"),
                    body  : _t("La remise semble mal configurée. Soyez sûr que la case 'Est une remise' soit cochée."),
                });
                return;
            }

            // Remove existing discounts
            var i = 0;
            while ( i < lines.length ) {
                if (lines[i].get_product() === product) {
                    order.remove_orderline(lines[i]);
                } else {
                    i++;
                }
            }

            // Add discount
            // We add the price as manually set to avoid recomputation when changing customer.
            var discount = - pc / 100.0 * order.get_total_with_tax();

            if( discount < 0 ){
                order.add_product(product, {
                    price: discount,
                    extras: {
                        price_manually_set: true,
                    },
                });
            }
        },
    });

    screens.define_action_button({
        'name': 'discount',
        'widget': DiscountButton,
        'condition': function(){
            return this.pos.config.module_pos_discount && this.pos.config.discount_product_ids;
        },
    });

});
