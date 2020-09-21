odoo.define('web_ui_stock_receipt.ReceiptMoveLineNumpad', function (require) {
    "use strict";

    var WebUiStockNumpad = require('web_ui_stock.Numpad');

    return WebUiStockNumpad.extend({
        init: function (row, name="") {
            this._super(row, name);
            this.qty_initial = row.quantity_done;
            this.qty_todo = row.quantity_to_do;
            this.unit = row.move_line.product_uom;
        },
    });
});
