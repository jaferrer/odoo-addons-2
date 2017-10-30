odoo.define('web.ListFixed', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var FormView = require('web.FormView');
    var common = require('web.list_common');
    var ListView = require('web.ListView');
    var utils = require('web.utils');
    var Widget = require('web.Widget');

    ListView.include({

        save_edition: function () {
            var result = this._super.apply(this, arguments);
            this.editor.form.$el.removeClass('oe_list_scroll_fix');
            return result;
        },

        start_edition: function () {
            var result = this._super.apply(this, arguments);
            this.editor.form.$el.addClass('oe_list_scroll_fix');
            return result;
        },

        cancel_edition: function (force) {
            var result = this._super.apply(this, arguments);
            this.editor.form.$el.removeClass('oe_list_scroll_fix');
            return result;
        }
    });
});