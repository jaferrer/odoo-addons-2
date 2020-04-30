odoo.define('web_ui_stock_product.ScanProductRowNumpad', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require('web.WebClient');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'ProductTableRow.Numpad',
        init: function (productMainList, productRow) {
            this._super(productMainList);
            this.productMainList = productMainList;
            this.productRow = productRow;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ProductTableRow renderElement");
            this.$('button.js_numpad_add_0').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_1').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_2').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_3').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_4').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_5').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_6').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_7').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_8').click(ev => { this.productMainList.delete_row(this) });
            this.$('button.js_numpad_add_9').click(ev => { this.productMainList.delete_row(this) });
        },
    });
});
