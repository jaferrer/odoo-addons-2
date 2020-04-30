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
            this.$('button.js_open_calculator').click(ev => { this._open_calculator() });

            this.btn_info = this.$('a.js_btn_info');
            this.btn_info.popover();
            this.btn_info.click(ev => this.btn_info.popover('show'));
            this.btn_info.blur(ev => this.btn_info.popover('destroy'));

            if (this.need_user_action){
                this.$el.addClass('info');
            }
        },

        _update_quantity: function () {
            this.product.quantity += 1;
            this.$('#product_quantity').text(this.product.quantity);
        },

        _open_calculator: function () {
            this.$('#quantity_numpad').toggleClass('d-none')
            this.$('#quantity_numpad_header').toggleClass('d-none')
        },

        _replace_product:function(product){
            this.id = product.id;
            this.product = product;
            this.renderElement();
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
