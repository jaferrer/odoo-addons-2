odoo.define('web_ui_stock_storage.StorageNavigate', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');
    var Numpad = require('web_ui_stock_storage.StorageNumpad');
    var Model = require('web.Model');
    let StockPickingType = new Model('stock.picking.type');
    let StockPicking = new Model('stock.picking');
    let StockMoveLine = new Model('stock.pack.operation');

    const STATES = {
        product: 1,
        location: 2,
        quantity: 3
    }

    return Widget.extend({
        template: 'StorageNavigate',
        barcode_scanner: null,
        activity: null,
        pickingId: null,
        moveLineId: null,
        moveLine: null,
        isLast: false,
        codeInput: null,
        state: STATES.product,
        showManualInput: true,
        hasQtyChanged: false,
        init: function (activity, pickingId, options = {}) {
            this._super();
            this.barcode_scanner = new BarcodeScanner();
            this.activity = activity;
            this.pickingId = parseInt(pickingId);

            // this.showManualInput = options.showManualInput;
        },
        renderElement: function () {
            this._super();
            this.codeInput = this.$('#search-code');

            this.$('#skip-move-line-btn').click(ev => {
                if (this.hasQtyChanged) {
                    this.state = STATES.picking;
                    this.renderState();
                } else {
                    this.next_move_line();
                }
            });

            this.$('#end-navigation-btn').click(ev => {
                this.end_navigation();
            });

            this.$('.picking-nav .picking-flex').click(ev => {
                if (this.state === STATES.location) {
                    this.scan("");
                } else if (this.state === STATES.product) {
                    new Numpad(this, this.moveLine.product.name).appendTo('body');
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
            this.barcode_scanner.disconnect();
            this._super();
        },
        register_scanner: function () {
            this.barcode_scanner.disconnect();
            this.codeInput.focus(() => {
                this.barcode_scanner.disconnect();
                this.codeInput.on('keyup', (e) => {
                    if (e.key === 'Enter') {
                        this.scan($(this.codeInput).val())
                    }
                })
            });
            this.codeInput.blur(() => {
                this.codeInput.off('keyup');
                this.barcode_scanner.connect(this.scan.bind(this));
            });
            this.barcode_scanner.connect(this.scan.bind(this));
        },
        init_title: function () {
            StockPicking.call('read', [[this.pickingId], ['name']]).then((res) => {
                this.activity.set_activity_title(res[0]['name']);
            });
        },
        init_navigation: function () {
            // TODO Verifier si le picking contient une seule operation. Dans ce cas, on skip l'etape 1 (pour les mouvements internes instantanés)
            // StockPicking.call('get_batch_move_line', [[this.pickingId], this.moveLineId])
            //     .then((moveLine) => {
            //         this.moveLine = moveLine;
            //         this.moveLineId = moveLine.id;
            //         this.nextLineId = moveLine.next_move_line_id;
            //         this.init_title();
            //         this.renderElement();
            //     }).fail((errors, event) => {
            //         let message = errors.data ? errors.data.message : "Une erreur est survenue"
            //         $.toast({
            //             text: message,
            //             icon: 'error'
            //         });
            //         event.preventDefault();
            //     });
        },
        validate_new_qty: function (qty) {
            this.hasQtyChanged = true;
            this.moveLine.qty_done = parseFloat(qty);
            this.renderQty();
            if (this.moveLine.qty_done === this.moveLine.qty_todo) {
                this.state = STATES.picking;
                this.renderState();
            }
        },
        next_move_line: function () {
            if (this.isLast) {
                this.end_navigation();
            } else {
                this.activity.init_fragment_storage_navigate(this.pickingId);
            }
        },
        end_navigation: function () {
            StockPicking.call('get_batch_move_lines_recap', [[this.batchId]])
                .then((batchMoveLines) => {
                    this.batchMoveLines = batchMoveLines;
                    for (let i = 0; i < this.batchMoveLines.length; i++) {
                        let moveLine = batchMoveLines[i]
                        this.isValid = moveLine.qty_todo === moveLine.qty_done;
                        if (!this.isValid) {
                            break;
                        }
                    }
                    this.renderElement();
                });
        },
        scan: function (code) {
            console.log(code);

            let goToNextStep = false;
            this.codeInput.val('');

            switch (this.state) {
                case STATES.product:
                    this.scanProduct(code);
                    break;
                case STATES.location:
                    this.scanLocation(code);
                    goToNextStep = true;
                    break;
                case STATES.quantity:
                    this.scanQuantity(code);
                    break;
            }

            if (goToNextStep) {
                if (this.state === STATES.picking) {
                    this.next_move_line();
                }
                this.state++;
                this.renderState();
            }
        },
        scanProduct: function (code) {
            StockPickingType.call('web_ui_get_storage_product_info_by_name', [[this.activity.pickingTypeId], code, this.pickingId])
                .then((moveLines) => {
                    let moveLine = moveLines[0];
                    this.moveLine = moveLine;
                    this.moveLineId = moveLine.id;
                    this.isLast = false;
                    this.state++;
                    this.renderElement();

                })
                .fail((errors, event) => {
                    console.log("Error print", errors, event);
                    event.preventDefault();
                });
        },
        scanLocation: function (code) {
            return true;
        },
        scanQuantity: function (code) {
            return true;
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
                this.$('#picking-qty-done').addClass('text-error');
            } else {
                this.$('#picking-qty-done').removeClass('text-success');
                this.$('#picking-qty-done').removeClass('text-error');
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

            this.$('#info-text').text("Scanner un article du chariot");
        },
        renderStateLocation: function () {
            this.$('#picking-location').addClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-quantity').removeClass('picking-focus');

            this.$('#info-text').text("Allez à l'emplacement demandé ou à nouvel emplacement");
        },
        renderStateQuantity: function () {
            this.$('#picking-location').removeClass('picking-focus');
            this.$('#picking-qty-done').removeClass('picking-focus');
            this.$('#picking-quantity').addClass('picking-focus');

            this.$('#info-text').text("Validez la quantité demandée et rangez les articles");
        },
    });
});