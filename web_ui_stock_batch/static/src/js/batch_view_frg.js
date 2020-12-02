odoo.define('web_ui_stock_batch.BatchView', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Model = require('web.Model');
    let StockPickingBatch = new Model('stock.picking.wave');

    return Widget.extend({
        template: 'BatchView',
        activity: null,
        batchId: null,
        batchMoveLines: [],
        isStarted: false,
        isCompleted: false,
        init: function (activity, batchId) {
            this._super(activity);
            this.activity = activity;
            this.batchId = parseInt(batchId);
            this.batchMoveLines = [];
        },
       renderElement: function() {
            this._super();
            this.$('#start-picking-btn').click(ev => {
                if (!this.isCompleted) {
                    this.activity.init_fragment_batch_navigate(this.batchId);
                }
                else {
                    this.activity.init_fragment_batch_recap(this.batchId);
                }
            });
        },
        start: function () {
            this._super();
            this.init_batch();
            this.init_title();
        },
        init_title: function () {
             StockPickingBatch.call('read', [[this.batchId], ['name']]).then((res) => {
                this.activity.set_activity_title(res[0]['name']);
            });
        },
        init_batch: function () {
            this.batchMoveLines = [];
            StockPickingBatch.call('get_batch_move_lines', [[this.batchId]])
                .then((batchMoveLines) => {
                    this.batchMoveLines = batchMoveLines;
                    for (let i = 0 ; i < this.batchMoveLines.length ; i++) {
                        let moveLine = batchMoveLines[i]
                        this.isStarted = !this.isStarted ? moveLine.qty_done > 0 : true;
                        this.isCompleted = moveLine.qty_todo === moveLine.qty_done;
                        if (!this.isCompleted) {
                            break;
                        }
                    }
                    this.renderElement();
                });
        },
    });
});
