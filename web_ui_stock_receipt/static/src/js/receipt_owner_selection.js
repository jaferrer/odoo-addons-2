odoo.define('web_ui_stock_receipt.ReceiptOwnerSelection', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'ReceiptOwnerSelectionTable',
        init: function (receiptMainList, owner) {
            this._super(receiptMainList);
            this.id = owner.id;
            this.name = owner.name;
        },
    });
});
