odoo.define('web_ui_stock_batch.BatchRecap', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Model = require('web.Model');
    let StockPickingBatch = new Model('stock.picking.wave');

    return Widget.extend({
        template: 'BatchRecap',
        activity: null,
        batchId: null,
        batchMoveLines: [],
        isValid: true,
        init: function (activity, batchId) {
            this._super(activity);
            this.activity = activity;
            this.batchId = parseInt(batchId);
            this.batchMoveLines = [];
        },
        renderElement: function () {
            this._super();
            this.$('#validate-picking-btn').click(ev => {
                this.validate_batch();
            });

            this.$('.move-line-item').click(ev => {
                let moveLineId = $(ev.currentTarget).attr('data-move_line_id')
                this.activity.init_fragment_batch_navigate(this.batchId, moveLineId, false);
            });
        },
        start: function () {
            this._super();
            this.init_recap();
            this.init_title();
        },
        init_title: function () {
            StockPickingBatch.call('read', [[this.batchId], ['name']]).then((res) => {
                this.activity.set_activity_title(res[0]['name']);
            });
        },
        init_recap: function () {
            this.batchMoveLines = [];
            StockPickingBatch.call('get_batch_move_lines_recap', [[this.batchId]])
                .then((batchMoveLines) => {
                    this.batchMoveLines = batchMoveLines;
                    for (let i = 0; i < this.batchMoveLines.length; i++) {
                        let moveLine = batchMoveLines[i]
                        this.isValid = moveLine.qty_todo === moveLine.qty_done;
                        if (!this.isValid) {
                            break;
                        }
                    }
                    this.renderElement();
                });
        },
        validate_batch: function () {
            this.batchMoveLines = [];
            StockPickingBatch.call('do_validate_batch_scan', [[this.batchId]])
                .then((result) => {
                    if (result) {
                        this.activity.init_fragment_batch_selection();
                    } else {
                        $.toast({
                            text: 'Impossible de valider la vague',
                            icon: 'error'
                        });
                    }
                })
                .fail((errors, event) => {
                    let message = errors.data ? errors.data.message : "Une erreur est survenue"
                    $.toast({
                        text: message,
                        icon: 'error'
                    });
                    event.preventDefault();
                });
        },
    });
});