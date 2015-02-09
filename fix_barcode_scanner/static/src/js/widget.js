openerp.fix_barcode_scanner = function(instance) {

    instance.stock.BarcodeScanner.include({
        connect: function(callback){
            var code = "";
            var timeStamp = 0;
            var timeout = null;

            this.handler = function(e){
                if(e.which === 13){
                    if(code.length >= 3){
                        callback(code);
                    }
                    code = "";
                    return;
                }
                code += String.fromCharCode(e.which);
            };

            $('body').on('keypress', this.handler);

        },
    });
}