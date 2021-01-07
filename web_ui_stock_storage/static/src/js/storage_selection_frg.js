odoo.define('web_ui_stock_storage.StorageSelection', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    return Widget.extend({
        template: 'StorageSelection',
        activity: null,
        pickingList: [],
        init: function (activity) {
            this._super(activity);
            this.activity = activity;
            this.pickingList = [];
        },
        renderElement: function() {
            this._super();
            this.$('.picking-item').click(ev => {
                let pickingId = $(ev.currentTarget).attr('data-picking_id')
                this.activity.init_fragment_storage_navigate(pickingId)
            });
            this.$('#no-picking-btn').addClass('hidden')
            this.$('#no-picking-btn').click(ev => {
                // todo rangement sans bon
            });
        },
        start: function () {
            this._super();
            this.init_pickings();
            this.init_title();
        },
        init_title: function () {
            this.activity.init_title();
        },
        init_pickings: function () {
            this.pickingList = []
            StockPickingType.call('web_ui_get_all_picking_storage', [[this.activity.pickingTypeId]])
                .then((pickingList) => {
                    this.pickingList = pickingList;
                    this.renderElement();
                });
        }
    });
});
