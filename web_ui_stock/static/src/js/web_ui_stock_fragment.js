odoo.define('web_ui_stock.StockFragment', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var BarcodeScanner = require('web_ui_stock.BarcodeScanner');

    return Widget.extend({
        barcode_scanner: null,
        codeInput: null,
        init: function () {
            this._super();
            this.barcode_scanner = new BarcodeScanner();
        },
        renderElement: function () {
            this._super();
            this.codeInput = this.$('#search-code');
            this.register_scanner();
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
        scan: function() {
            throw new Error("Vous devez implementer la méthode");
        }
    });
});