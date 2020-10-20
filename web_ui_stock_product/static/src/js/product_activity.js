odoo.define('web_ui_stock_product.ProductActivity', function (require) {
    "use strict";

    var StockActivity = require('web_ui_stock.StockActivity');
    var core = require('web.core');

    var ProductSelection = require('web_ui_stock_product.ProductSelection');
    var ProductView = require('web_ui_stock_product.ProductView');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    var ProductActivity = StockActivity.extend({
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.storageScreen = options.storage_screen || false;
            this.is_internal_move = options.type === 'internal_move';
            this.auto_max_qty = this.is_internal_move;
        },
        start: function () {
            this._super();
            if (!this.is_internal_move) {
                this.init_fragment_product_selection();
            } else {
                 this.init_fragment_product_view(null);
            }
        },
        init_title: function () {
            StockPickingType.call('read', [[this.pickingTypeId], ['name']]).then((res) => {
                this.set_activity_title(res[0]['name']);
            });
        },
        init_fragment_product_selection: function () {
            while (this.fragmentsStack.length > 0) {
                this.fragmentsStack.pop().destroy();
            }
            var productSelection = new ProductSelection(this);
            this.fragmentsStack.push(productSelection);
            this.init_fragment();
            productSelection.appendTo(this.activityContainer);
        },
        init_fragment_product_view: function (ownerId) {
            var productView = new ProductView(this, ownerId);
            this.fragmentsStack.push(productView);
            this.init_fragment();
            productView.appendTo(this.activityContainer);
        },
        continue_to_storage: function (picking) {
            this.do_action('stock.ui.storage', {
                'picking_type_id': this.pickingTypeId,
                'storage_screen': this.storageScreen,
                'picking_id': picking.id
            });
        },
        back_to_handling_screen: function (picking={}) {
            this.do_action('stock.ui.storage_handling', {
                'picking_type_id': this.pickingTypeId,
                'picking_id': picking.id,
                'picking_name': picking.name
            });
        },
    });

    core.action_registry.add('stock.ui.product', ProductActivity);
    return ProductActivity;
});
