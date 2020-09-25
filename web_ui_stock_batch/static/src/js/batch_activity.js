odoo.define('web_ui_stock_batch.BatchActivity', function (require) {
    "use strict";

    var StockActivity = require('web_ui_stock.StockActivity');
    var core = require('web.core');

    var BatchSelection = require('web_ui_stock_batch.BatchSelection');
    var BatchView = require('web_ui_stock_batch.BatchView');
    var BatchNavigate = require('web_ui_stock_batch.BatchNavigate');
    var BatchRecap = require('web_ui_stock_batch.BatchRecap');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    var BatchActivity = StockActivity.extend({
        start: function () {
            this._super();
            this.init_fragment_batch_selection();
        },
        init_title: function () {
            StockPickingType.call('read', [[this.pickingTypeId], ['name']]).then((res) => {
                this.set_activity_title(res[0]['name']);
            });
        },
        init_fragment_batch_selection: function () {
            while (this.fragmentsStack.length > 0) {
                this.fragmentsStack.pop().destroy();
            }
            var batchSelection = new BatchSelection(this);
            this.fragmentsStack.push(batchSelection);
            this.init_fragment();
            batchSelection.appendTo(this.activityContainer);
        },
        init_fragment_batch_view: function (batchId) {
            var batchView = new BatchView(this, batchId);
            this.fragmentsStack.push(batchView);
            this.init_fragment();
            batchView.appendTo(this.activityContainer);
        },
        init_fragment_batch_navigate: function (batchId, moveLineId=null, loadNextLine= true) {
            let navigateOptions = {
                skipFirstStep: false,
                canTapLocation: true,
                showManualInput: false
            }
            var batchNavigate = new BatchNavigate(this, batchId, navigateOptions, moveLineId, loadNextLine);
            while (this.fragmentsStack.slice(-1)[0].__proto__.template !== 'BatchView') {
                this.fragmentsStack.pop().destroy();
            }
            this.fragmentsStack.push(batchNavigate);
            this.init_fragment();
            batchNavigate.appendTo(this.activityContainer);
        },
        init_fragment_batch_recap: function (batchId) {
            var batchNavigate = new BatchRecap(this, batchId);
            this.fragmentsStack.push(batchNavigate);
            this.init_fragment();
            batchNavigate.appendTo(this.activityContainer);

        },
    });

    core.action_registry.add('stock.ui.batch', BatchActivity);
    return BatchActivity;
});
