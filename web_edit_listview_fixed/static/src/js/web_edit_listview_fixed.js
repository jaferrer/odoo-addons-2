odoo.define('web.EditListFormFixed', function (require) {
    "use strict";

    var ListView = require('web.ListView');
    ListView.include({

        resize_field: function (field, cell) {
            var result = this._super.apply(this, arguments);
            var pos_ok = $('.oe_edition')[0];
             if (pos_ok !== 'undefined' && pos_ok !== undefined && field.$el.parents('.modal-dialog').length == 0) {
                field.$el.css({'top': pos_ok.offsetTop});
            }
            return result;
        },
    });
});