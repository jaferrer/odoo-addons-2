odoo.define('web_ui_stock_storage.StorageNavigate', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Numpad = require('web_ui_stock_storage.StorageNumpad');
    var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let StockPicking = new Model('stock.picking');
    let StockMoveLine = new Model('stock.pack.operation');

    const STATES = {
        product: 1,
        location: 2,
        quantity: 3,
        lot: 4
    }

    return Widget.extend(BarcodeHandlerMixin, {
        template: 'StorageNavigate',
        activity: null,
        pickingId: null,
        moveLineIds: [],
        moveLines: [],
        moveLine: null,
        isLast: false,
        codeInput: null,
        state: STATES.product,
        showManualInput: true,
        hasQtyChanged: false,
        init: function (activity, pickingId, options = {}) {
            this._super.apply(this, arguments);
            BarcodeHandlerMixin.init.apply(this, arguments);
            this.activity = activity;
            this.pickingId = parseInt(pickingId);

            this.showManualInput = options.showManualInput;
            this.showManualInput = true;
        },
        renderElement: function () {
            this._super();
            this.codeInput = this.$('#search-code');

            this.$('#skip-move-line-btn').click(ev => {
                if (this.state === STATES.product) {
                    return;
                }
            });

            this.$('#force-qty-btn').click(ev => {
                if (this.state === STATES.quantity) {
                    this.validate_move_line();
                }
            });

            this.$('#end-navigation-btn').click(ev => {
                this.end_navigation();
            });

            this.$('.picking-nav .picking-flex').click(ev => {
                if (this.state === STATES.quantity) {
                    new Numpad(this, this.moveLine.name).appendTo('body');
                }
            });

            this.renderState();
            this.renderQty();
            this.register_scanner();
        },
        start: function () {
            this._super();
            this.init_navigation();
        },
        destroy: function () {
            $('.modal-backdrop').remove();
            this._super();
        },
        register_scanner: function () {
            this.codeInput.focus(() => {
                this.stop_listening()
                this.codeInput.on('keyup', (e) => {
                    if (e.key === 'Enter') {
                        this.on_barcode_scanned($(this.codeInput).val())
                    }
                })
            });
            this.codeInput.blur(() => {
                this.codeInput.off('keyup');
                this.start_listening()
            });
        },
        init_title: function () {
            StockPicking.call('read', [[this.pickingId], ['name']]).then((res) => {
                this.activity.set_activity_title(res[0]['name']);
            });
        },
        init_navigation: function () {
            this.init_title();
            StockPickingType.call('web_ui_has_one_operation_left', [[this.activity.pickingTypeId], this.pickingId])
            .then((res) => {
                if (res.empty) {
                    this.activity.notifyError("Transfert indisponible");
                    setTimeout(function() { window.history.back(); }, 1000);
                } else if (res.last_operation) {
                    this.isLast = true;
                    this.scanProduct(res.last_operation);
                }
            });
        },
        validate_new_qty: function (qty) {
            this.hasQtyChanged = true;
            this.moveLine.qty_done = parseFloat(qty);
            this.renderQty();

            if (this.moveLine.qty_done === this.moveLine.qty_todo) {
                this.validate_move_line();
            }
        },
        validate_move_line: function () {
            StockPickingType.call('web_ui_get_storage_add_move', [[this.activity.pickingTypeId], this.moveLine.id, this.moveLine.qty_done])
                .then(() => {
                    this.next_move_line();
                });
        },
        next_move_line: function () {
            if (this.isLast) {
                this.end_navigation();
            } else {
                this.activity.init_fragment_storage_navigate(this.pickingId);
            }
        },
        end_navigation: function () {
            StockPickingType.call('web_ui_get_storage_validate_move', [[this.activity.pickingTypeId], this.pickingId])
                .then(() => window.history.back());
        },
        on_barcode_scanned: function (code) {
            console.log(code);
            $(this.codeInput).val('');
            switch (this.state) {
                case STATES.product:
                    this.scanProduct(code);
                    break;
                case STATES.location:
                    this.scanLocation(code);
                    break;
                case STATES.quantity:
                    this.scanQuantity(code);
                    break;
            }
        },
        scan: this.on_barcode_scanned.bind(this), //Compatibility
        scanProduct: function (code) {
            this.moveLines = []
            StockPickingType.call('web_ui_get_storage_product_info_by_name', [[this.activity.pickingTypeId], code, this.pickingId])
                .then((moveLines) => {
                    moveLines.forEach(moveLine => {
                        this.moveLine = moveLine;
                        this.moveLines.push(this.moveLine);

                        if (moveLine.tracking !== "none") {
                            this.$("#product_num_lot").text(moveLine.num_lot);
                            if (!moveLine.num_lot) {
                                // this.$("#product_num_lot").text(tracking.num_lot);
                                // this.state = STATES.lot;
                            }
                        }

                        if (this.state !== STATES.lot) {
                            this.state = STATES.location;
                        }
                    });
                    this.renderElement();
                })
                .fail((errors, event) => {
                    this.activity.notifyError("Produit introuvable");
                    event.preventDefault();
                });
        },
        scanLot: function (code) {
            return true;
            // StockPickingType.call('web_ui_get_tracking_by_name', [[this.pickingTypeId], ean, this.productId])
            //         .then((tracking) => {
            //             this.$("#product_num_lot").text(tracking.num_lot);
            //             this.state = 3;
            //         })
            //         .fail((errors, event) => {
            //             event.preventDefault();
            //         });
        },
        scanLocation: function (code) {
            let moveLineIds = this.moveLines.map(x => x.id)
            StockPickingType.call('web_ui_get_storage_location_info_by_name', [[this.activity.pickingTypeId], code, moveLineIds])
                .then((moveLine) => {
                    this.moveLine = moveLine;
                    this.moveLines = [this.moveLine];

                    this.state = STATES.quantity;
                    this.renderElement();
                })
                .fail((errors, event) => {
                    if (confirm("L'emplacement " + code + " ne correspond pas au produit, souhaitez vous le modifier ?")) {
                        this.scanNewLocation(code);
                    }
                    event.preventDefault();
                });
        },
        scanNewLocation: function (code) {
            StockPickingType.call('web_ui_get_storage_new_location_info_by_name', [[this.activity.pickingTypeId], code, this.moveLine.id])
                .then((moveLine) => {
                    this.updateLocation(moveLine, code);
                })
                .fail((errors, event) => {
                    this.activity.notifyError("Emplacement introuvable");
                    event.preventDefault();
                });
        },
        scanQuantity: function (code) {
            if (this.moveLine.default_code === code || this.moveLine.name === code) {
                this.validate_new_qty(this.moveLine.qty_done + 1)
            } else {
                this.activity.notifyError("Mauvais produit scanné");
            }
        },
        updateLocation: function (moveLine, locationCode) {
            StockMoveLine.call('change_location_from_scan_storage', [[moveLine.id], locationCode])
                .then((location) => {
                    this.moveLine.location_id = location.name;
                    this.state = STATES.quantity;
                    this.renderElement();
                });
        },
        renderQty: function () {
            // Gestion de l'affichage de la quantité uniquement
            if (!this.moveLine) {
                return;
            }

            this.$('#picking-qty-done').text(this.moveLine.qty_done);

            if (this.moveLine.qty_done === this.moveLine.qty_todo) {
                this.$('#picking-qty-done').addClass('text-success');
            } else if (this.moveLine.qty_done > this.moveLine.qty_todo) {
                this.$('#picking-qty-done').addClass('text-danger');
            } else {
                this.$('#picking-qty-done').removeClass('text-success');
                this.$('#picking-qty-done').removeClass('text-danger');
            }
        },
        renderState: function () {
            switch (this.state) {
                case STATES.product:
                    this.renderStateProduct();
                    break;
                case STATES.location:
                    this.renderStateLocation();
                    break;
                case STATES.quantity:
                    this.renderStateQuantity();
                    break;
            }
        },
        renderStateProduct: function () {
            this.$('#picking-location').removeClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-quantity').removeClass('picking-focus');

            this.$('#picking-qty').addClass('hidden');
            this.$('#force-qty-li').addClass('disabled');
            this.$('#skip-move-line-btn').addClass('disabled');

            this.$('#info-text').text("Scanner un article du chariot");
        },
        renderStateLocation: function () {
            this.$('#picking-location').addClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-quantity').removeClass('picking-focus');

            this.$('#picking-qty').addClass('hidden');
            this.$('#force-qty-li').addClass('disabled');
            this.$('#skip-move-line-btn').removeClass('disabled');

            this.$('#info-text').text("Scannez l'emplacement demandé ou un nouvel emplacement");
        },
        renderStateQuantity: function () {
            this.$('#picking-location').removeClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-quantity').addClass('picking-focus');

            this.$('#picking-qty').removeClass('hidden');
            this.$('#force-qty-li').removeClass('disabled');
            this.$('#skip-move-line-btn').removeClass('disabled');

            this.$('#info-text').text("Validez la quantité demandée et rangez les articles");
        },
    });
});