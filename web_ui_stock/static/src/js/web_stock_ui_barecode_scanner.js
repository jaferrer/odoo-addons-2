odoo.define('web_ui_stock.BarcodeScanner', function (require) {
    return require('web.core').Class.extend({
        connect: function (callback) {
            var code = "";
            this.handler = function (e) {
                switch (e.key) {
                    case "ArrowDown":
                    case "ArrowUp":
                    case "ArrowLeft":
                    case "ArrowRight":
                    case "Escape":
                    case "Control":
                    case "Alt":
                    case "Shift":
                        return;
                    case "Backspace":
                        code = code.substring(1);
                    case "Enter":
                        if (code.length >= 3) {
                            callback(code);
                        }
                        code = "";
                        return;
                    default:
                        code += e.key;
                }
            };
            $(window).on('keyup', this.handler);
        },
        disconnect: function () {
            $(window).off('keyup', this.handler);
        },
    });
});