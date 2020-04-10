odoo.define('web_ui_packing.PackingRow.Detail', function (require) {
    "use strict";

    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var data = require('web.data');
    var WebClient = require("web.WebClient");
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    return Widget.extend({
        template: 'PickingTableRow.Detail',
        init: function (pickingMainList, pickingRow, data) {
            this._super(pickingMainList);
            this.pickingMainList = pickingMainList;
            this.package_names = data.package_names;
            this.operations = data.operations;
            this.pickingRow = pickingRow;
        },
        start: function () {
            this._super();
        },
        renderElement: function () {
            this._super();
            this.picking_operations_table_body = this.$('#picking_operations_table_body');

            console.log("Render", this.template);
            this.btn_put_in_pack = this.$('#btn_put_in_pack');
            this.btn_quit_detail = this.$('#btn_quit_detail');
            this.btn_quit_detail.click((ev) => this.action_exit(ev));
            this.btn_put_in_pack.click((ev) => this.put_in_pack(ev));
            this.render_operation()
        },
        render_operation: function(){
            this.operations.forEach(op => {
                this.picking_operations_table_body.append(QWeb.render('PackingRow.Detail.Operation', {operation: op}))
            });
            this.$('span.js_minus').click((ev) => this.action_decrease_qty(ev));
            this.$('span.js_plus').click((ev) => this.action_increase_qty(ev));
            this.$('button.js_set_todo_in_done').click((ev) => this.action_set_todo_in_done(ev));
            this.$('button.js_raz').click((ev) => this.action_raz(ev));
        },
        put_in_pack: function (ev) {
            let payload = $.makeArray(this.$('.js_qty')).map((el, idx) => [$(el).data('operation-id'), $(el).val()]);
            console.log(payload);
            let sp_web_ui_set_operations_qty_params = {
                model: 'stock.picking',
                method: 'web_ui_set_operations_qty',
                args: [[this.pickingRow.id, payload]],
            };
            rpc.query(sp_web_ui_set_operations_qty_params).then((result) => {
                this.picking_operations_table_body.empty();
                this.operations = result.operations;
                this.package_names = result.package_names;
                if (this.operations.length === 0){
                    this.action_exit()
                } else {
                    this.render_operation()
                }
            });
            console.log("put_in_pack", ev)
        },
        action_raz: function (ev) {
            let operation_id = $(ev.currentTarget).data('operation-id');
            let input = this.$(`input.js_qty[data-operation-id=${operation_id}]`);
            input.val(0);
            console.log("action_set_todo_in_done", ev)
        },
        action_exit: function (ev) {
            this.pickingMainList.exit_detail(this)
        },
        action_set_todo_in_done: function (ev) {
            let operation_id = $(ev.currentTarget).data('operation-id');
            let input = this.$(`input.js_qty[data-operation-id=${operation_id}]`);
            const max_value = this.operations.find(it => it.uuid === operation_id).qty_todo;
            input.val(max_value);
            console.log("action_set_todo_in_done", ev)
        },
        action_increase_qty: function (ev) {
            let operation_id = $(ev.currentTarget).data('operation-id');
            let input = this.$(`input.js_qty[data-operation-id=${operation_id}]`);
            const new_value = Number.parseInt(input.val()) + 1;
            const max_value = this.operations.find(it => it.uuid === operation_id).qty_todo;
            if (new_value <= max_value) {
                input.val(new_value)
            }
        },
        action_decrease_qty: function (ev) {
            let operation_id = $(ev.currentTarget).data('operation-id');
            let input = this.$(`input.js_qty[data-operation-id=${operation_id}]`);
            const new_value = Number.parseInt(input.val()) - 1;
            if (new_value >= 0) {
                input.val(new_value)
            }
        },
    });
});
