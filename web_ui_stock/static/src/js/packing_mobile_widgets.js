odoo.define('web_ui_stock.MobileWidget', function (require) {
"use strict";
    // This widget makes sure that the scaling is disabled on mobile devices.
    // Widgets that want to display fullscreen on mobile phone need to extend this
    // widget.
    return require('web.Widget').extend({
        start: function () {
            if (!$('#oe-mobilewidget-viewport').length) {
                $('head').append('<meta id="oe-mobilewidget-viewport" name="viewport" content="initial-scale=1.0; maximum-scale=1.0; user-scalable=0;">');
            }
            return this._super();
        },
        destroy: function () {
            $('#oe-mobilewidget-viewport').remove();
            return this._super();
        },
    });
});
