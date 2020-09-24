odoo.define('web_ui_stock_product.Numpad', function (require) {
    "use strict";

    var WebUiStockNumpad = require('web_ui_stock.Numpad');

    return WebUiStockNumpad.extend({
        init: function (row, name="") {
            this._super(row, name);
            this.qty_initial = row.product.quantity;
        },
        validate_and_exit: function (ev) {
            this.row.increaseQty(this.qty_value, true);
            this.exit();
        },
    });
});
