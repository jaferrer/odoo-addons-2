odoo.define('web_ui_stock_batch.BatchMoveLineNumpad', function (require) {
    "use strict";

    var WebUiStockNumpad = require('web_ui_stock.Numpad');

    return WebUiStockNumpad.extend({
        init: function (row, name="") {
            this._super(row, name);
            this.row = row;
            this.qty_initial = row.quantity_done;
            this.qty_todo = row.quantity_to_do
            this.display_quantity = row.display_qty;
        },
    });
});
