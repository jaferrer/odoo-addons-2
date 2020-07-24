odoo.define('web_ui_stock_batch.BatchMoveLineLot', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'BatchMoveLineLot',
        init: function (batchMainList, batchMoveLineRow) {
            this._super(batchMainList);
            this.batchMainList = batchMainList;
            this.batchMoveLineRow = batchMoveLineRow;
            this.product = this.batchMoveLineRow.product;
            this.invalid_number = "";
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("BatchMoveLineLot renderElement");
        },
    });
});
