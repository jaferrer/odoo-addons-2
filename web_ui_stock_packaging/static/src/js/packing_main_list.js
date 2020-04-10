odoo.define('web_ui_packing.PackingMainWidget', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var PackingRow = {
        Row: require('web_ui_packing.PackingRow'),
        Detail: require('web_ui_packing.PackingRow.Detail'),
        Error: require('web_ui_packing.PackingRow.Error')
    };
    var rpc = require('web.rpc');

    var NeedUserAttentionModal = Widget.extend({
        template: 'NeedUserAttentionModal',
        init: function (parent, rows, title) {
            this.pickingMainList = parent;
            this.rows = rows;
            this.title = title;
            this.display_cn23_message = rows.some(el => el.picking.country_need_cn23);
            this.display_other_pickings = rows.some(el => el.picking.other_picking);
            this.other_pickings = rows
                .filter(it => it.picking.other_picking)
                .flatMap(it => (it.picking.other_picking || "").split(","))
                .map(it => it.trim())
        },
        renderElement: function () {
            this._super();
            this.$('#validate_need_user_action_modal').click(ev => {
                this.rows.forEach(it => it.need_user_action = false);
                this.pickingMainList.print_label_for_rows(this.rows);
                this.pickingMainList.exit_need_action()
            });
            this.$('#exit_need_user_action_modal').click(ev => {
                this.pickingMainList.exit_need_action()
            });
        },
    });

    var PackingMainWidget = Widget.extend(AbstractAction.prototype, {
        template: 'PackingMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.rows = [];
            this.selected_packaging_computer = 0;
            this.barcode_scanner = new BarcodeScanner();
        },
        renderElement: function () {
            this._super();
            this.picking_table = this.$('#picking_table');
            this.$('#_exit').click((ev) => window.history.back());
            this.picking_table_body = this.$('#picking_table_body');
            this.picking_split_detail = this.$('#picking_split_detail');
            let spt_name_get_params = {
                model: 'stock.picking.type',
                method: 'name_get',
                args: [[this.pickingTypeId]],
            };
            rpc.query(spt_name_get_params).then((res) => this._set_view_title(res[0][1]));
            this._init_packaging_computer();
            this._connect_scanner();
            this.need_user_action_modal_hook = this.$('#need_user_action_modal_hook');
            this.$('#search_picking').focus(() => {
                this._disconnect_scanner();
                this.$('#search_picking').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan(this.$('#search_picking').val())
                    }
                })
            });
            this.$('#search_picking').blur(() => {
                this.$('#search_picking').off('keyup');
                this._connect_scanner();
            });
            this.$('#clear_search_picking').click(() => {
                console.log('clear_search_picking');
                this.$('#search_picking').val('');
                this.$('#search_picking').focus()
            });
            this.$('#btn_delete_all_rows').click(() => {
                console.log('btn_delete_all_rows');
                this.$('[data-error-row]').remove();
                this.rows.forEach((row) => this.delete_row(row));

            });
            this.$('#btn_process_all_rows').click(() => {
                console.log('btn_process_all_rows');
                this.$('[data-error-row]').remove();
                this.print_label_for_rows(this.rows);
            });
        },
        _init_packaging_computer: function () {
            let printer_computer_params = {
                model: 'poste.packing',
                method: 'search_read',
                args: [[]],
            };
            rpc.query(printer_computer_params).then((res) => {
                let packaging_section = this.$('#packing_printer_choice');
                res.forEach(res => {
                    packaging_section.append($(document.createElement('button'))
                        .addClass('btn')
                        .addClass('btn-default')
                        .addClass('btn-packaging')
                        .attr('data-packaging-computer-id', res.id)
                        .attr('data-packaging-computer-code', res.code)
                        .text(res.name)
                    );
                });
                this.$('button.btn-packaging').click((ev) => this.on_select_packaging_computer(ev));
            });

        },
        on_select_packaging_computer: function (ev) {
            let el = $(ev.currentTarget);
            this.$('button.btn-packaging').removeClass('btn-success');
            this.$('button.btn-packaging').addClass('btn-default');
            el.toggleClass('btn-success');
            el.toggleClass('btn-default');
            this.selected_packaging_computer = el.data('packaging-computer-id');
            this.$('#btn_process_all_rows').prop("disabled", false);
            this.$('.js_print_picking').prop("disabled", false);
        },
        _set_view_title: function (title) {
            $("#view_title").text(title);
        },
        start: function () {
            this._super();
            // window.openerp.webclient.set_content_full_screen(true);
        },
        _connect_scanner: function () {
            this.barcode_scanner.connect(this.scan.bind(this));
        },
        _disconnect_scanner: function () {
            this.barcode_scanner.disconnect();
        },
        get_header: function () {
            return this.getParent().get_header();
        },
        scan: function (ean) {
            console.log(ean);
            this.$('#search_picking').val('');
            let spt_picking_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_picking_info_by_name',
                args: [[this.pickingTypeId], ean],
            };
            rpc.query(spt_picking_info_params)
                .always(() => {
                    if (!this.$('#big_helper').hasClass('hidden')) {
                        this.$('#big_helper').addClass('hidden')
                    }
                })
                .then((pick) => {
                    let pickingsIds = this.rows.map(it => it.picking.id);
                    if (!pickingsIds.includes(pick.id)) {
                        let row = new PackingRow.Row(this, pick);
                        this.rows.push(row);
                        row.appendTo(this.picking_table_body);
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    new PackingRow.Error(this, {
                        'title': errors.data.arguments[0],
                        'message': errors.data.arguments[1]
                    }).appendTo(this.picking_table_body);
                    event.preventDefault();
                });
        },
        delete_row: function (row) {
            console.log('delete_row', row);
            row.$el.remove();
            this.rows.splice(this.rows.indexOf(row), 1);
            console.log('delete_row', this.rows);
        },


        print_label_for_rows: function (rows) {
            if (this.selected_packaging_computer < 0) {
                alert("Veuiller selectionner un poste de packing")
            }
            this.$('[data-error-row]').remove();
            let sp_print_label_params = {
                model: 'stock.picking',
                method: 'web_ui_print_label',
                args: [[row.picking.id], this.selected_packaging_computer],
            };
            rows.filter(row => !row.need_user_action).forEach((row) => {
                rpc.query(sp_print_label_params)
                    .then(result => row.on_success_print())
                    .fail((error, event) => {
                        console.log("Error print", error, event);
                        row.on_error_print(error);
                        event.preventDefault();
                    });
            });
            let need_action_rows = rows.filter(row => row.need_user_action);
            if (need_action_rows.lenght > 0) {
                this.need_user_action_view = new NeedUserAttentionModal(this, need_action_rows,
                    "Action à faire avant l'impression des étiquettes"
                );
                this.need_user_action_view.appendTo(this.need_user_action_modal_hook);
                this.picking_table.toggleClass('hidden');
                this.$('#mass_btn').toggleClass('hidden');
                this.need_user_action_modal_hook.toggleClass('hidden');
                this._disconnect_scanner();
            }
        },
        print_label_for_row: function (row) {
            this.print_label_for_rows([row])
        },
        cut_picking_for_row: function (row) {
            let sp_stock_operation_todo_params = {
                model: 'stock.picking',
                method: 'web_ui_get_data_stock_operation_todo',
                args: [[row.picking.id]],
            };
            rpc.query(sp_stock_operation_todo_params).then((result) => {
                this.picking_table.toggleClass('hidden');
                this.$('#mass_btn').toggleClass('hidden');
                this.picking_split_detail.toggleClass('hidden');
                new PackingRow.Detail(this, row, result).appendTo(this.picking_split_detail);
            }).fail((errors, event) => {
                console.log("Error print", errors, event);
                new PackingRow.Error(this, {
                    'title': row.picking.name,
                    'message': errors.data.arguments[1]
                }).replace(row.$el);
                event.preventDefault();
            });
        },
        exit_detail: function (detail) {
            this.picking_table.toggleClass('hidden');
            this.$('#mass_btn').toggleClass('hidden');
            this.picking_split_detail.toggleClass('hidden');
            this.picking_split_detail.empty();
            let sp_picking_info_one_params = {
                model: 'stock.picking',
                method: 'web_ui_get_picking_info_one',
                args: [[detail.pickingRow.id]],
            };
            rpc.query(sp_picking_info_one_params).then((result) => {
                detail.pickingRow._replace_picking(result)
            })
        },
        exit_need_action: function () {
            this.picking_table.toggleClass('hidden');
            this.$('#mass_btn').toggleClass('hidden');
            this.need_user_action_view = false;
            this.need_user_action_modal_hook.toggleClass('hidden');
            this.need_user_action_modal_hook.empty();
            this._connect_scanner()
        },
    });


    core.action_registry.add('stock.ui.packaging', PackingMainWidget);
    return PackingMainWidget;
});
