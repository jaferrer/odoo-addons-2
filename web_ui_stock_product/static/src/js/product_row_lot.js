odoo.define('web_ui_stock_product.ProductRow.Lot', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'ProductTableRow.Lot',
        init: function (productView, productRow) {
            this._super(productView);
            this.productView = productView;
            this.productRow = productRow;
            this.invalid_number = "";
        },
        renderElement: function () {
            this._super();
            this.$('button.js_delete_product_lot').click(ev => { this.deleteRowLot(this.productRow) });
        },
        deleteRowLot: function (row) {
            this.productView.removeRow(row);
            this.productView.requestProduct();
            destroy();
        },
    });
});
