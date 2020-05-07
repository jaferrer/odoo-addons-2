odoo.define('web_ui_stock_product.ScanProductRow', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require('web.WebClient');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'ProductTableRow',
        init: function (productMainList, product) {
            this._super(productMainList);
            this.productMainList = productMainList;
            this.id = product.id;
            this.product = product;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ProductTableRow renderElement");
            this.$('button.js_delete_product').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_open_numpad').click(ev => { this.productMainList.open_numpad(this) });

            if (this.product.tracking === 'serial') {
                this.$('button.js_open_numpad').addClass('d-none');
            }
            if (this.product.tracking === "lot" || this.product.tracking === "serial" &&
                this.product.lot_id === false) {
                this.productMainList.open_need_num_lot(this);
            }
        },
        _update_quantity: function () {
            this.product.quantity += 1;
            this.$('#product_quantity').text(this.product.quantity);
        },
        _update_num_lot: function (product_infos) {
            this.product.lot_id = product_infos.lot_id;
            this.product.lot_name = product_infos.lot_name;
            this.$('#lot_name').text(this.product.lot_name);
        },
        validate_new_qty: function (numpad) {
            this.product.quantity = numpad.quantity;
            this.$('#product_quantity').text(this.product.quantity);
            this.productMainList.exit_numpad(numpad);
        },
        on_error_print: function (error) {
            this.$el.addClass('warning');
            this.btn_info.toggleClass('d-none');
            this.btn_info.attr('data-content', error.data.arguments.filter(Boolean).join("<br/>") || error.message)
        },
        on_success_print: function () {
            this.$el.addClass('success')
        },
    });
});
