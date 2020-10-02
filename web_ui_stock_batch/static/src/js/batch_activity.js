odoo.define('web_ui_stock_batch.BatchActivity', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');

    var BatchSelection = require('web_ui_stock_batch.BatchSelection');
    var BatchView = require('web_ui_stock_batch.BatchView');
    var BatchNavigate = require('web_ui_stock_batch.BatchNavigate');
    var BatchRecap = require('web_ui_stock_batch.BatchRecap');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    var BatchActivity = Widget.extend({
        template: 'BatchActivity',
        fragmentsStack: [],
        activityContainer: null,
        backButton: null,
        pickingTypeId: null,
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
        },
        renderElement: function() {
            this._super();

            this.activityContainer = this.$('#activity-container');
            this.backButton = this.$('#back-btn');

            this.$('#exit-btn').click((ev) => {
                this.exit_activity();
            });

            this.backButton.click((ev) => {
                this.return_to_previous_fragment();
            });
        },
        start: function () {
            this._super();
            this.init_fragment_batch_selection();
        },
        set_activity_title: function (title) {
            this.$("#view_title").text(title);
        },
        init_title: function () {
            StockPickingType.call('read', [[this.pickingTypeId], ['name']]).then((res) => {
                this.set_activity_title(res[0]['name']);
            });
        },
        init_fragment: function () {
            this.activityContainer.empty();
            if (this.fragmentsStack.length > 1) {
                this.backButton.removeClass('hidden');
            }
            else {
                this.backButton.addClass('hidden');
            }
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
        init_fragment_batch_navigate: function (batchId, moveLineId=null) {
            let navigateOptions = {
                skipFirstStep: false,
                canTapLocation: true,
                showManualInput: false
            }
            var batchNavigate = new BatchNavigate(this, batchId, navigateOptions, moveLineId);
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
        exit_activity: function () {
            window.history.back();
        },
        return_to_previous_fragment: function () {
            if (this.fragmentsStack.length <= 1) {
                return;
            }
            this.fragmentsStack.pop().destroy();
            this.init_fragment();
            this.fragmentsStack[this.fragmentsStack.length - 1].appendTo(this.activityContainer);
        }
    });

    core.action_registry.add('stock.ui.batch', BatchActivity);
    return BatchActivity;
});
