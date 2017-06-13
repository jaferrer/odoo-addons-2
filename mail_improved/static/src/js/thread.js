openerp.mail_improved = function (instance) {

    instance.mail.ThreadMessage.include({
        bind_events: function () {
            var self = this;
            this._super();
            this.$('.oe_more_recipients').on('click', self.on_show_recipients);
            this.$('.oe_more_hidden_recipients').on('click', self.on_hide_recipients);
        },

        on_show_recipients: function () {
            this.$('.oe_more_hidden_recipients, .oe_hidden_recipients').show();
            this.$('.oe_more_recipients').hide();
            return false;
        },

        on_hide_recipients: function () {
            this.$('.oe_more_hidden_recipients, .oe_hidden_recipients').hide();
            this.$('.oe_more_recipients').show();
            return false;
        }

    });

};