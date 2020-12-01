odoo.define('web_ui_storage.StorageRow', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require("web.WebClient");
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;
    var Numpad = require('web_ui_stock.Numpad');

    return Widget.extend({
        template: 'StorageTableRow',
        init: function (pickingMainList, picking) {
            this._super(pickingMainList);
            this.pickingMainList = pickingMainList;
            this.id = picking.id;
            this.picking = picking;
            this.need_user_action = this.picking.other_picking || this.picking.country_need_cn23
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            console.log("StorageTableRow renderElement");
            this.$('button.js_delete_picking').click(ev => { this.pickingMainList.delete_row(this) });
            this.$('button.js_open_numpad').click(ev => { this.open_numpad() });
        },
        _replace_picking:function(picking){
            this.id = picking.id;
            this.picking = picking;
            this.renderElement();
        },
        open_numpad: function () {
            new Numpad(this).appendTo('body');
        },
        on_error_print: function (error) {
            this.$el.addClass('warning');
            this.btn_info.toggleClass('hidden');
            this.btn_info.attr('data-content', error.data.arguments.filter(Boolean).join("<br/>") || error.message)
        },
    });
});
