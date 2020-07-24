odoo.define('web_ui_stock_receipt.ReceiptResult', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'ReceiptResult',
        init: function (mainList, result) {
            this._super(mainList, "");
            this.result = result;
        },
    });
});
