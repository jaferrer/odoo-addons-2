odoo.define('web_ui_stock_receipt.ReceiptPickingSelection', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'ReceiptPickingSelectionTable',
        init: function (receiptMainList, stock_picking) {
            this._super(receiptMainList);
            this.receiptMainList = receiptMainList;
            this.id = stock_picking.id;
            this.selected_receipt_picking = stock_picking;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("ReceiptPickingSelectionTable renderElement");
            this.$el.click(ev => { this.select_this_picking(this.id) });
        },
        select_this_picking: function (picking_id) {
            if (!this.receiptMainList.$('#big_helper').hasClass('hidden')) {
                this.receiptMainList.$('#big_helper').addClass('hidden');
            }
            this.receiptMainList.selected_receipt_picking = this.id;
            this.receiptMainList._load_receipt_move_lines(picking_id);
            this.receiptMainList.$('#receipt_picking_selection_table').toggleClass('hidden');
            this.receiptMainList.$('#move_line_table').toggleClass('hidden');
            this.receiptMainList.$('#manual_scan_product').toggleClass('hidden');
            this.receiptMainList.$('#validate_receipt').toggleClass('hidden');
        },
    });
});
