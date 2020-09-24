odoo.define('web_ui_stock_product.ProductRow', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Numpad = require('web_ui_stock_product.Numpad');
    var Model = require('web.Model');
    let ProductProduct = new Model('product.product');

    return Widget.extend({
        template: 'ProductTableRow',
        init: function (productView, product) {
            this._super(productView);
            this.productView = productView;
            this.id = product.id;
            this.product = product;
        },
        start: function () {
            this._super();
            if (this.productView.type === 'internal_move' && !this.product.location_id) {
                this.productView.requestLocation(this);
            }
            
            if (this.product.tracking === "lot" || this.product.tracking === "serial" &&
                this.product.lot_id === false) {
                this.productView.reequestNumLot(this);
            }
        },
        renderElement: function () {
            this._super();
            this.$('button.js_delete_product').click(ev => { this.deleteRow() });

            this.$().click(ev => { this.openNumpad(this); });

            if (this.product.tracking === 'serial') {
                this.$('button.js_open_numpad').addClass('hidden');
            }
        },
        increaseQty: function (amount=1, reset=false) {
            this.product.quantity = reset ? amount : amount + this.product.quantity;
            this.renderElement();
        },
        updateNumLot: function (product_infos) {
            this.product.lot_id = product_infos.lot_id;
            this.product.lot_name = product_infos.lot_name;
            this.renderElement();
        },
        openNumpad: function () {
            var self = this;
            ProductProduct.call('web_ui_get_product_info', [[this.product.id]])
                .then(() => { new Numpad(self, this.product.name).appendTo('body') });
        },
        deleteRow: function () {
            this.productView.removeRow(this);
            this.productView.requestProduct();
            this.destroy();
        },
    });
});
