odoo.define('web_ui_stock_product.ProductSelection', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');

    return Widget.extend({
        template: 'ProductSelection',
        activity: null,
        ownerList: [],
        init: function (activity) {
            this._super(activity);
            this.activity = activity;
            this.ownerList = [];
        },
        renderElement: function() {
            this._super();
            this.$('.owner-item').click(ev => {
                let ownerId = $(ev.currentTarget).attr('data-owner_id')
                this.activity.init_fragment_product_view(ownerId)
            });
        },
        start: function () {
            this._super();
            this.init_owners();
            this.init_title();
        },
        init_title: function () {
            this.activity.init_title();
        },
        init_owners: function () {
            this.ownerList = []
            StockPickingType.call('get_all_picking_owners', [[this.activity.pickingTypeId]])
                .then((ownerList) => {
                    this.ownerList = ownerList;
                    this.renderElement();
                });
        }
    });
});
