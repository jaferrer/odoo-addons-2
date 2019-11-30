odoo.define('web.EditListFormFixed', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var FormView = require('web.FormView');
    var common = require('web.list_common');
    var ListView = require('web.ListView');
    var utils = require('web.utils');
    var Widget = require('web.Widget');

    ListView.include({

        resize_field: function (field, cell) {
            var result = this._super.apply(this, arguments);
            var pos_ok = $('.oe_edition')[0];
            console.log('field :', field)
            console.log('cell :', cell)
            console.log('pos_ok', pos_ok)
            field.$el.css({'top': pos_ok.offsetTop});
            return result;
        },
    });
});