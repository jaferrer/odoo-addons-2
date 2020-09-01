odoo.define('web_ui_stock.AlertError', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        init: function (message, type, dismissAuto) {
            this._super(message, type, dismissAuto);
            this.message = message;
            this.type = type;
            this.dismissAuto = dismissAuto;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
        },
    });
});
