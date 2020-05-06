odoo.define('web_ui_stock_product.ScanProductRow.Error', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require("web.WebClient");
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'ScanProductRow.Error',
        init: function (productMainList, error) {
            this._super(productMainList);
            this.productMainList = productMainList;
            this.error = error;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ErrorRow renderElement");
            this.$('button.js_delete_product').click(ev => this.productMainList.delete_row(this));
        },
    });
});
