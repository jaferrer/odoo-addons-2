odoo.define('web_ui_stock_batch.BatchSelection', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var Model = require('web.Model');
    let StockPickingBatch = new Model('stock.picking.wave');

    return Widget.extend({
        template: 'BatchSelection',
        activity: null,
        batchList: [],
        init: function (activity) {
            this._super(activity);
            this.activity = activity;
            this.batchList = [];
        },
        renderElement: function() {
            this._super();
            this.$('.batch-item').click(ev => {
                let batchId = $(ev.currentTarget).attr('data-batch_id')
                this.activity.init_fragment_batch_view(batchId)
            });
        },
        start: function () {
            this._super();
            this.init_batches();
            this.init_title();
        },
        init_title: function () {
            this.activity.init_title();
        },
        init_batches: function () {
            this.batchList = []
            StockPickingBatch.call('get_all_picking_batches', [])
                .then((batchList) => {
                    this.batchList = batchList;
                    this.renderElement();
                });
        }
    });
});
