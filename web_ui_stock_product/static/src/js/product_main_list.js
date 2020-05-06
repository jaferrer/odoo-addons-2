odoo.define('web_ui_stock_product.ScanProductMainWidget', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ScanProductRow = {
        Row: require('web_ui_stock_product.ScanProductRow'),
        Error: require('web_ui_stock_product.ScanProductRow.Error'),
        Numpad: require('web_ui_stock_product.ScanProductRow.Numpad')
    };
    var rpc = require('web.rpc');

    var ScanProductMainWidget = Widget.extend(AbstractAction.prototype, {
        template: 'ScanProductMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.rows = [];
            this.selected_scan_product_computer = 0;
            this.barcode_scanner = new BarcodeScanner();
        },
        renderElement: function () {
            this._super();
            this.product_table = this.$('#product_table');
            this.$('#_exit').click((ev) => window.history.back());
            this.product_table_body = this.$('#product_table_body');
            this.quantity_numpad = this.$('#quantity_numpad');
            let spt_name_get_params = {
                model: 'stock.picking.type',
                method: 'name_get',
                args: [[this.pickingTypeId]],
            };
            rpc.query(spt_name_get_params).then((res) => this._set_view_title(res[0][1]));
            this._init_scan_product_computer();
            this._connect_scanner();
            this.need_user_action_modal_hook = this.$('#need_user_action_modal_hook');
            this.$('#search_product').focus(() => {
                this._disconnect_scanner();
                this.$('#search_product').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan(this.$('#search_product').val())
                    }
                })
            });
            this.$('#search_product').blur(() => {
                this.$('#search_product').off('keyup');
                this._connect_scanner();
            });
            this.$('#clear_search_product').click(() => {
                console.log('clear_search_product');
                this.$('#search_product').val('');
                this.$('#search_product').focus()
            });
            this.$('#btn_delete_all_rows').click(() => {
                console.log('btn_delete_all_rows');
                this.$('[data-error-row]').remove();
                this.rows.forEach((row) => this.delete_row(row));

            });
            this.$('#btn_process_all_rows').click(() => {
                console.log('btn_process_all_rows');
                this.$('[data-error-row]').remove();
            });
            this.$('button.js_validate_scan').click(ev => { this.validate_scan() });
        },
        _init_scan_product_computer: function () {
            let printer_computer_params = {
                model: 'poste.product',
                method: 'search_read',
                args: [[]],
            };
            rpc.query(printer_computer_params).then((res) => {
                let scan_product_section = this.$('#scan_product_printer_choice');
                res.forEach(res => {
                    scan_product_section.append($(document.createElement('button'))
                        .addClass('btn')
                        .addClass('btn-default')
                        .addClass('btn-scan-product')
                        .attr('data-scan-product-computer-id', res.id)
                        .attr('data-scan-product-computer-code', res.code)
                        .text(res.name)
                    );
                });
                this.$('button.btn-scan-product').click((ev) => this.on_select_scan_product_computer(ev));
            });

        },
        on_select_scan_product_computer: function (ev) {
            let el = $(ev.currentTarget);
            this.$('button.btn-scan-product').removeClass('btn-success');
            this.$('button.btn-scan-product').addClass('btn-default');
            el.toggleClass('btn-success');
            el.toggleClass('btn-default');
            this.selected_scan_product_computer = el.data('scan-product-computer-id');
            this.$('#btn_process_all_rows').prop("disabled", false);
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
        scan: function (name) {
            console.log(name);
            this.$('#search_product').val('');
            let pp_product_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_product_info_by_name',
                args: [[this.pickingTypeId], name],
            };
            rpc.query(pp_product_info_params)
                .always(() => {
                    if (!this.$('#big_helper').hasClass('d-none')) {
                        this.$('#big_helper').addClass('d-none')
                    }
                })
                .then((produ) => {
                    let productsIds = this.rows.map(it => it.product.id);
                    if (!productsIds.includes(produ.id)) {
                        let row = new ScanProductRow.Row(this, produ);
                        this.rows.push(row);
                        row.appendTo(this.product_table_body);
                    }
                    else {
                        let row = this.rows.find(it => it.product.id == produ.id);
                        row._update_quantity();
                    }
                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    new ScanProductRow.Error(this, {
                        'title': errors.data.arguments[0],
                        'message': errors.data.arguments[1]
                    }).appendTo(this.product_table_body);
                    event.preventDefault();
                });
        },
        delete_row: function (row) {
            console.log('delete_row', row);
            row.$el.remove();
            this.rows.splice(this.rows.indexOf(row), 1);
            console.log('delete_row', this.rows);
        },
        open_numpad: function (row) {
            let pp_product_info_params = {
                model: 'product.product',
                method: 'web_ui_get_product_info',
                args: [[row.product.id]],
            };
            rpc.query(pp_product_info_params).then((result) => {
                this.product_table.toggleClass('d-none');
                this.$('#mass_btn').toggleClass('d-none');
                this.$('#manual_scan').toggleClass('d-none');
                this.quantity_numpad.toggleClass('d-none');
                new ScanProductRow.Numpad(this, row).appendTo(this.quantity_numpad);
            }).fail((errors, event) => {
                console.log("Error print", errors, event);
                new ScanProductRow.Error(this, {
                    'title': row.product.name,
                    'message': errors.data.arguments[1]
                }).replace(row.$el);
                event.preventDefault();
            });
        },
        exit_numpad: function (numpad) {
            this.product_table.toggleClass('d-none');
            this.$('#mass_btn').toggleClass('d-none');
            this.$('#manual_scan').toggleClass('d-none');
            this.quantity_numpad.toggleClass('d-none');
            this.quantity_numpad.empty();
        },
        validate_scan: function () {
            let product_infos = [];
            this.rows.forEach(row => product_infos.push({
                'id': row.product.id,
                'quantity': row.product.quantity}
                ));
            let do_validate_scan_params = {
                model: 'stock.picking.type',
                method: 'do_validate_scan',
                args: [[this.pickingTypeId], product_infos],
            };
            rpc.query(do_validate_scan_params).then(() => { window.history.back() })
        },
    });


    core.action_registry.add('stock.ui.product', ScanProductMainWidget);
    return ScanProductMainWidget;
});
