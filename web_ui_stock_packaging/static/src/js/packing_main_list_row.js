odoo.define('web_ui_packing.PackingRow', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require("web.WebClient");
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'PickingTableRow',
        init: function (pickingMainList, picking
        ) {
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
            console.log("PickingTableRow renderElement");
            this.$('button.js_delete_picking').click(ev => { this.pickingMainList.delete_row(this) });
            this.$('button.js_print_picking').click(ev => { this.pickingMainList.print_label_for_row(this) });
            if (this.pickingMainList.selected_packaging_computer > 0){
                this.$('button.js_print_picking').prop( "disabled", false);
            }
            this.btn_print = this.$('button.js_print_picking');

            this.btn_info = this.$('a.js_btn_info');
            this.btn_cut_picking = this.$('button.js_cut_picking');
            this.btn_info.popover();
            this.btn_info.click(ev => this.btn_info.popover('show'));
            this.btn_info.blur(ev => this.btn_info.popover('destroy'));
            this.$('button.js_cut_picking').click(ev => { this.pickingMainList.cut_picking_for_row(this) });

            if (this.picking.not_allowed_reason){
                this.$el.addClass('danger');
                this.btn_print.toggleClass('d-none');
                this.btn_cut_picking.toggleClass('d-none');
                this.btn_info.toggleClass('d-none');
                this.btn_info.attr('data-content', this.picking.not_allowed_reason);
            } else if (this.need_user_action){
                this.$el.addClass('info');
            }
        },
        _replace_picking:function(picking){
            this.id = picking.id;
            this.picking = picking;
            this.renderElement();
        },
        on_error_print: function (error) {
            this.$el.addClass('warning');
            this.btn_info.toggleClass('d-none');
            this.btn_info.attr('data-content', error.data.arguments.filter(Boolean).join("<br/>") || error.message)
        },
        on_success_print: function () {
            this.$el.addClass('success')
        },
    });
});
