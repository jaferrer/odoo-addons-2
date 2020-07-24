odoo.define('web_ui_stock_batch.BatchSelectionTable', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'BatchSelectionTable',
        init: function (batchMainList, picking_batch) {
            this._super(batchMainList);
            this.batchMainList = batchMainList;
            this.id = picking_batch.id;
            this.picking_batch = picking_batch;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("BatchSelectionTable renderElement");
            this.$('button.js_select_batch').click(ev => { this.select_this_batch(this.id) });
        },
        select_this_batch: function (batch_id) {
            if (!this.batchMainList.$('#big_helper').hasClass('hidden')) {
                this.batchMainList.$('#big_helper').addClass('hidden');
            }
            this.batchMainList.selected_batch = this.picking_batch;
            this.batchMainList._load_batch_move_lines(batch_id);
            this.batchMainList.$('#batch_selection_table').toggleClass('hidden');
            this.batchMainList.$('#move_line_table').toggleClass('hidden');
            this.batchMainList.$('#manual_scan_location').toggleClass('hidden');
        },
    });
});
