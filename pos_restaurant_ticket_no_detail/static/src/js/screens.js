var ReceiptScreenWidgetNoDetail = ReceiptScreenWidget.extend({
    template: 'ReceiptScreenWidgetNoDetail',

    show: function(){
        this._super();
        var self = this;

        this.render_receipt_no_detail();

        if (this.should_auto_print()) {
            this.print();
            if (this.should_close_immediately()){
                this.click_next();
            }
        } else {
            this.lock_screen(false);
        }

    },

    render_receipt_no_detail: function () {
        var order = this.pos.get_order();
        this.$('.pos-receipt-container').html(QWeb.render('PosTicketNoDetail', {
            widget: this,
            order: order,
            receipt: order.export_for_printing(),
            orderlines: order.get_orderlines(),
            paymentlines: order.get_paymentlines(),
        }));
    }
});