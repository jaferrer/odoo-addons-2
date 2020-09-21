odoo.define('web_ui_storage.StorageRow.Error', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require("web.WebClient");
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'PackingRow.Error',
        init: function (pickingMainList, error) {
            this._super(pickingMainList);
            this.pickingMainList = pickingMainList;
            this.error = error;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ErrorRow renderElement");
            this.$('button.js_delete_picking').click(ev => this.pickingMainList.delete_row(this));
        },
    });
});
