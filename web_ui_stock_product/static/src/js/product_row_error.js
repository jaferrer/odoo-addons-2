odoo.define('web_ui_stock_product.ProductRow.Error', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'ProductRow.Error',
        init: function (productView, error) {
            this._super(productView);
            this.productView = productView;
            this.error = error;
        },
        renderElement: function () {
            this._super();
            this.$('button.js_delete_product').click(ev => this.deleteRow());
        },
        deleteRow: function () {
            this.destroy();
        }
    });
});
