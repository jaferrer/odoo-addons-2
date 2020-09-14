odoo.define('web_ui_stock_batch.BatchNumpad', function (require) {
    "use strict";

    var WebUiStockNumpad = require('web_ui_stock.Numpad');

    return WebUiStockNumpad.extend({
        init: function (fragment, name="") {
            this._super(fragment, name);
            this.row = fragment;
            this.qty_initial = fragment.moveLine.qty_done;
            this.qty_todo = fragment.moveLine.qty_todo
        },
    });
});
