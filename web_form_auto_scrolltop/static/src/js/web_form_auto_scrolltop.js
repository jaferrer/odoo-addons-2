odoo.define('web_form_auto_scrolltop.FormView', function(require) {
    "use strict";

    var core = require('web.core');
    var FormView = core.view_registry.get('form');

    FormView.include({
         do_show: function (options) {
            this._super.apply(this, arguments);
            window.scrollTo(0, 0);
         },
    });
});