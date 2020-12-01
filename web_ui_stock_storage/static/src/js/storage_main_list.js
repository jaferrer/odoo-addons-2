odoo.define('web_ui_storage.storageMainWidget', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var Numpad = require('web_ui_stock.Numpad');
    var StorageRow = {
        Row: require('web_ui_storage.StorageRow'),
        Error: require('web_ui_storage.StorageRow.Error')
    };
    var rpc = require('web.rpc');

    var StorageMainWidget = Widget.extend(AbstractAction.prototype, {
        template: 'StorageMainWidget',
        init: function (parent, action, options) {
            this._super(parent, action, options);
            this.pickingTypeId = parseInt(options.picking_type_id || "0");
            this.storageScreen = options.storage_screen || false;
            this.state = 1;
            // On a un nom de picking lorsque l'on veut ranger directement un chariot qu'on vient de créer
            this.pickingName = options.picking_name || "";
            this.pickingId = "0";
            this.productId = "0";
            this.productBarcode = "";
            this.productName = "";
            this.changing_location = false;
            this.moveLineQty = "0";
            this.moveLineId = "0";
            this.moveLines = [];
            this.barcode_scanner = new BarcodeScanner();
        },
        renderElement: function () {
            this._super();
            this.picking_table = this.$('#picking_table');
            this.$('#btn_exit').click((ev) => window.history.back());
            this.storage_table_body = this.$('#storage_table_body');
            this.picking_split_detail = this.$('#picking_split_detail');
            this.$('#manual_product_scan').addClass('hidden');
            this.$('#manual_location_scan').addClass('hidden');
            this.$('#manual_tracking_scan').addClass('hidden');
            this.$('#error').addClass('hidden');
            this.$('button.js_change_location').click(ev => {
                this.allow_change_location()
            });
            this.$('button.js_confirm_location').click(ev => {
                this.confirm_location()
            });
            this.$('button.js_validate_scan').click(ev => {
                this.validate_scan()
            });
            this.screen = this.$("#screen");
            let spt_name_get_params = {
                model: 'stock.picking.type',
                method: 'name_get',
                args: [[this.pickingTypeId]],
            };
            rpc.query(spt_name_get_params).then((res) => this._set_view_title(res[0][1]));
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
            this.$('#search_location').focus(() => {
                this._disconnect_scanner();
                this.$('#search_location').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan(this.$('#search_location').val(), this.changing_location)
                    }
                })
            });
            this.$('#search_location').blur(() => {
                this.$('#search_location').off('keyup');
                this._connect_scanner();
            });
            this.$('#clear_search_location').click(() => {
                console.log('clear_search_location');
                this.$('#search_location').val('');
                this.$('#search_location').focus()
            });
            this.$('#search_tracking').focus(() => {
                this._disconnect_scanner();
                this.$('#search_tracking').on('keyup', (e) => {
                    if (e.key == 'Enter') {
                        this.scan(this.$('#search_tracking').val())
                    }
                })
            });
            this.$('#search_tracking').blur(() => {
                this.$('#search_tracking').off('keyup');
                this._connect_scanner();
            });
            this.$('#clear_search_tracking').click(() => {
                console.log('clear_search_tracking');
                this.$('#search_tracking').val('');
                this.$('#search_tracking').focus()
            });
            // Si on arrive sur cet écran depuis le gestionnaire de chariot
            if (this.storageScreen) {
                this.$('#back_to_handling_screen').removeClass('hidden');
            }
            this.$('#back_to_handling_screen').click(() => {
                this.back_to_handling_screen()
            });
            // Si on arrive sur cet écran après la création d'un chariot
            if (this.pickingName) {
                this.scan(this.pickingName)
            }
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
        scan: function (ean, changing_location = false) {
            console.log(ean);
            this.$('#search_picking').val('');
            let spt_picking_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_picking_info_by_name',
                args: [[this.pickingTypeId], ean],
            };
            let spt_product_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_storage_product_info_by_name',
                args: [[this.pickingTypeId], ean, this.pickingId],
            };
            let spt_location_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_storage_location_info_by_name',
                args: [[this.pickingTypeId], ean, this.moveLines],
            };
            let spt_new_location_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_storage_new_location_info_by_name',
                args: [[this.pickingTypeId], ean, this.moveLineId],
            };
            let spt_tracking_info_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_tracking_by_name',
                args: [[this.pickingTypeId], ean, this.productId],
            };
            if (this.state == 1) {
                console.log("Recherche d'un BRANG");
                rpc.query(spt_picking_info_params)
                    .always(() => {
                        if (!this.$('#big_helper').hasClass('hidden')) {
                            this.$('#big_helper').addClass('hidden')
                        }
                    })
                    .then((pick) => {
                        this.$('#manual_product_scan').removeClass('hidden');
                        this.$('#manual_scan').addClass('hidden');
                        this.$('#display_picking').text(pick.name);
                        this.$('#wait_product').addClass('active')
                        this.$('#error').addClass('hidden');
                        this.pickingId = pick.id;
                        this.state = 2;
                    })
                    .fail((errors, event) => {
                        console.log("Error ", errors, event);
                        this.$('#error').removeClass('hidden');
                        this.$('#error_text').text(errors.data.arguments[0] + " - " + errors.data.arguments[1]);
                        event.preventDefault();
                    });
            }
            if (this.state == 2) {
                console.log("Recherche d'un product");
                rpc.query(spt_product_info_params)
                    .then((moveLines) => {
                        moveLines.forEach(moveLine => {
                            let row = new StorageRow.Row(this, moveLine);
                            row.appendTo(this.storage_table_body);
                            this.productId = moveLine.product_id;
                            this.productBarcode = moveLine.default_code;
                            this.productName = moveLine.name;
                            this.moveLines.push(moveLine.id);
                            this.$("#product_name").text(moveLine.name);
                            this.$("#product_code").text(moveLine.default_code);
                            if (moveLine.tracking != "none") {
                                this.$("#product_num_lot").text(moveLine.num_lot);
                                this.$('#span_product_num_lot').removeClass('hidden');
                                if (!moveLine.num_lot) {
                                    this.$('#manual_tracking_scan').removeClass('hidden');
                                    this.$('#wait_tracking').removeClass('hidden');
                                    this.$('#wait_tracking').addClass('active');
                                    this.state = 21;
                                } else {
                                    this.$('#manual_location_scan').removeClass('hidden');
                                    this.$('#wait_location').addClass('active');
                                    this.$('#span_product_location').removeClass('hidden');
                                    this.$('#span_product_location').addClass('orange');
                                    this.state = 3;
                                }
                            } else {
                                this.$('#manual_location_scan').removeClass('hidden');
                                this.$('#wait_location').addClass('active');
                                this.$('#span_product_location').removeClass('hidden');
                                this.$('#span_product_location').addClass('orange');
                                this.state = 3;
                            }
                        });
                        console.log("RP " + this.state);
                        this.$('#manual_product_scan').addClass('hidden');
                        this.$('#wait_product').addClass('ok');
                        this.$('#wait_product').removeClass('active');
                        this.$('#error').addClass('hidden');
                        this.$('#search_product').val('');
                        this.$('#span_product_code').removeClass('hidden');
                        this.$('#span_product_name').removeClass('hidden');
                    })
                    .fail((errors, event) => {
                        console.log("Error print", errors, event);
                        this.$('#error').removeClass('hidden');
                        this.$('#error_text').text(errors.data.arguments[0] + " - " + errors.data.arguments[1]);
                        event.preventDefault();
                    });
            }
            if (this.state == 21) {
                console.log("RP21 " + this.state);
                rpc.query(spt_tracking_info_params)
                    .then((tracking) => {
                        this.$("#product_num_lot").text(tracking.num_lot);
                        this.$('#manual_product_scan').addClass('hidden');
                        this.$('#wait_tracking').addClass('ok');
                        this.$('#manual_location_scan').removeClass('hidden');
                        this.$('#wait_location').addClass('active');
                        this.$('#span_product_location').removeClass('hidden');
                        this.$('#span_product_location').addClass('orange');
                        this.state = 3;
                    })
                    .fail((errors, event) => {
                        console.log("Error print", errors, event);
                        this.$('#error').removeClass('hidden');
                        this.$('#error_text').text(errors.data.arguments[0] + " - " + errors.data.arguments[1]);
                        event.preventDefault();
                    });
            }
            if (this.state == 3) {
                console.log("Recherche d'un emplacement");
                if (!changing_location) {
                     rpc.query(spt_location_info_params)
                         .then((moveLine) => {
                            this.moveLines.push(moveLine.id);
                            console.log("id " + moveLine.id);
                            this.moveLineId = moveLine.id;
                            this.moveLineQty = moveLine.qty;
                            let row = new StorageRow.Row(this, moveLine);
                            this.storage_table_body.empty();
                            row.appendTo(this.storage_table_body);
                            this.$('#error').addClass('hidden');
                            this.$('#helper_location').removeClass('hidden');
                            this.$('#manual_location_scan').addClass('hidden');
                            this.$('button.js_change_location').removeClass('hidden');
                            this.$('button.js_confirm_location').removeClass('hidden');
                        })
                        .fail((errors, event) => {
                            console.log("Error print", errors, event);
                            this.$('#error').removeClass('hidden');
                            this.$('#error_text').text(errors.data.arguments[0] + " - " + errors.data.arguments[1]);
                            event.preventDefault();
                        });
                } else {
                     rpc.query(spt_new_location_info_params)
                         .then((moveLine) => {
                            this.update_location(moveLine, ean);
                            this.moveLines.push(moveLine.id);
                            console.log("id " + moveLine.id);
                            this.moveLineId = moveLine.id;
                            this.moveLineQty = moveLine.qty;
                            let row = new StorageRow.Row(this, moveLine);
                            this.storage_table_body.empty();
                            row.appendTo(this.storage_table_body);
                            this.$('#error').addClass('hidden');
                            this.$('#helper_location').removeClass('hidden');
                            this.$('#manual_location_scan').addClass('hidden');
                            this.$('button.js_change_location').removeClass('hidden');
                            this.$('button.js_confirm_location').removeClass('hidden');
                        })
                        .fail((errors, event) => {
                            console.log("Error print", errors, event);
                            this.$('#error').removeClass('hidden');
                            this.$('#error_text').text(errors.data.arguments[0] + " - " + errors.data.arguments[1]);
                            event.preventDefault();
                        });
                }
            }
            if (this.state == 4) {
                console.log("Recherche d'un produit");
                if (this.productBarcode == ean || this.productName == ean) {
                    console.log("Saisie de la quantité");
                    this.$('#manual_location_scan').addClass('hidden');
                    this.$('#confirm_product').addClass('ok');
                    this.$('#confirm_product').removeClass('active');
                    this.$('#confirm_quantity').addClass('active');
                    this.$('#span_product_qty_saisie').removeClass('hidden');
                    this.open_numpad();
                } else {
                    console.log("Error");
                    this.$('#error').removeClass('hidden');
                    this.$('#error_text').text(ean + " - Produit différent");
                }
            }
        },
        confirm_location: function () {
            this.changing_location = false;
            this.state = 4;
            this.$("#qty").text(this.moveLineQty);
            this.$('#span_product_qty').removeClass('hidden');
            this.$('#span_product_location').removeClass('orange');
            this.$('#manual_product_scan').removeClass('hidden');
            this.$('#manual_location_scan').addClass('hidden');
            this.$('#manual_location_scan > div').removeClass('waiting-background');
            this.$('#wait_location').addClass('ok');
            this.$('#wait_location').removeClass('active');
            this.$('#confirm_product').addClass('active');
            this.$('#helper_location').addClass('hidden');
            this.$('button.js_change_location').addClass('hidden');
            this.$('button.js_confirm_location').addClass('hidden');
            this.$('#scan_location_classic').removeClass('hidden');
            this.$('#scan_location_change').addClass('hidden');
        },
        allow_change_location: function () {
            this.changing_location = true;
            this.$('#helper_location').addClass('hidden');
            this.$('#manual_location_scan').removeClass('hidden');
            this.$('#manual_location_scan > div').addClass('waiting-background');
            this.$('#scan_location_classic').addClass('hidden');
            this.$('#scan_location_change').removeClass('hidden');
        },
        update_location: function (moveLine, location_name) {
               let sml_update_move_line_info_params = {
                model: 'stock.move.line',
                method: 'change_location_from_scan_storage',
                args: [[this.id], location_name],
            };
            rpc.query(sml_update_move_line_info_params)
                .then(() => moveLine.location_id = location_name);
        },
        open_numpad: function () {
            console.log("Open numpad");
            new Numpad(this, this.productBarcode).appendTo('body');
        },
        validate_new_qty: function (numpad) {
            // Sauvegarde du move
            console.log("Save " + this.moveLineId + " - " + numpad.qty_value);
            let do_add_scan_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_storage_add_move',
                args: [[this.pickingTypeId], this.moveLineId, numpad.quantity],
            };
            rpc.query(do_add_scan_params)
                .then(() => {
                    this.$('#manual_product_scan').removeClass('hidden');
                    this.$('#manual_scan').addClass('hidden');
                    this.$('#wait_product').addClass('active')
                    this.$('#confirm_product').removeClass('ok')
                    this.$('#wait_product').removeClass('ok')
                    this.$('#wait_location').removeClass('ok')
                    this.$('#confirm_quantity').removeClass('active')
                    this.$('#error').addClass('hidden');
                    this.$('#search_product').val('');
                    this.$('#search_location').val('');
                    this.$('#open_numpad').addClass('hidden');
                    this.productBarcode = "";
                    this.productName = "";
                    this.$("#product_name").text("");
                    this.$("#product_code").text("");
                    this.$("#qty").text("");
                    this.$('#span_product_code').addClass('hidden');
                    this.$('#span_product_name').addClass('hidden');
                    this.$('#span_product_location').addClass('hidden');
                    this.$('#span_product_qty').addClass('hidden');
                    this.$('#span_product_qty_saisie').addClass('hidden');
                    this.storage_table_body.empty();
                    this.state = 2;
                });
        },
        validate_scan: function () {
            console.log("Save ");
            let do_validate_scan_params = {
                model: 'stock.picking.type',
                method: 'web_ui_get_storage_validate_move',
                args: [[this.pickingTypeId], this.pickingId],
            };
            rpc.query(do_validate_scan_params).then(() => {
                window.history.back()
            })
        },
        back_to_handling_screen: function () {
            // supprime la vue de scan
            this.$('#big_helper').parent().parent().empty();
            this.do_action('stock.ui.storage_handling', {'picking_type_id': this.pickingTypeId});
        }
    });


    core.action_registry.add('stock.ui.storage', StorageMainWidget);
    return StorageMainWidget;
});
