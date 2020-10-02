odoo.define('web_ui_stock_storage.StorageActivity', function (require) {
    "use strict";

    var StockActivity = require('web_ui_stock.StockActivity');
    var core = require('web.core');

    var StorageSelection = require('web_ui_stock_storage.StorageSelection');
    var StorageNavigate = require('web_ui_stock_storage.StorageNavigate');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    var StorageActivity = StockActivity.extend({
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.storageScreen = options.storage_screen || false;
            this.pickingId = options.picking_id || false;
        },
        start: function () {
            this._super();
            if (this.pickingId) {
                this.init_fragment_storage_navigate(this.pickingId);
            }
            else {
                this.init_fragment_storage_selection();
            }
        },
        init_title: function () {
            StockPickingType.call('read', [[this.pickingTypeId], ['name']]).then((res) => {
                this.set_activity_title(res[0]['name']);
            });
        },
        init_fragment_storage_selection: function () {
            while (this.fragmentsStack.length > 0) {
                this.fragmentsStack.pop().destroy();
            }
            var storageSelection = new StorageSelection(this);
            this.fragmentsStack.push(storageSelection);
            this.init_fragment();
            storageSelection.appendTo(this.activityContainer);
        },
        init_fragment_storage_navigate: function (pickingId) {
            let navigateOptions = {}
            var storageNavigate = new StorageNavigate(this, pickingId, navigateOptions);
            while (this.fragmentsStack.length && this.fragmentsStack.slice(-1)[0].__proto__.template !== 'StorageSelection') {
                this.fragmentsStack.pop().destroy();
            }
            this.fragmentsStack.push(storageNavigate);
            this.init_fragment();
            storageNavigate.appendTo(this.activityContainer);
        },
    });

    core.action_registry.add('stock.ui.storage', StorageActivity);
    return StorageActivity;
});
