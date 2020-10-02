odoo.define('web_ui_stock_product.ScanProductRow.Lot', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require('web.WebClient');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'ProductTableRow.Lot',
        init: function (productMainList, productRow) {
            this._super(productMainList);
            this.productMainList = productMainList;
            this.productRow = productRow;
            this.invalid_number = "";
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ProductTableRow renderElement");
            this.$('button.js_delete_product_lot').click(ev => { this.delete_row_lot(this.productRow) });
        },
        delete_row_lot: function (row) {
            this.productMainList.delete_row(row);
            this.productMainList.exit_need_num_lot();
        },
    });
});
