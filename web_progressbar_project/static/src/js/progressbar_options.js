odoo.define('web_progress_bar.option', function(require) {
"use strict";

    var basic_fields = require('web.basic_fields');
    var utils = require('web.utils');
    var rpc = require('web.rpc');

    basic_fields.FieldProgressBar.include({
        init: function () {
            this._super.apply(this, arguments);
            self.display_value = this.nodeOptions.display_value;

            if(this.nodeOptions.default_value) {
                this.max_value = this.recordData[this.nodeOptions.max_value];
            }
        },

        /**
         * Renders the value
         *
         * @private
         * @param {Number} v
         */
        _render_value: function (v) {
            var _self = this;
            var value = this.value;
            var max_value = this.max_value;
            if (!isNaN(v)) {
                if (this.edit_max_value) {
                    max_value = v;
                } else {
                    value = v;
                }
            }
            value = value || 0;
            max_value = max_value || 0;

            var widthComplete;
            if (value <= max_value) {
                widthComplete = value / max_value * 100;
            } else {
                widthComplete = 100;
            }

            rpc.query({
                model: 'set.progressbar.color',
                method: 'assign_progress_bar_color',
                args: [[]],
            }).then(function (result) {
                if (result[0]) {
                    for (var ranges = 0; ranges < result.length; ranges++) {
                        _self.$('.o_progress').toggleClass('o_progress_overflow', value > max_value);
                        _self.$('.o_progress').addClass('progress');
                        _self.$('.o_progressbar_complete').addClass('progress-bar');

                        if (max_value != 0 && widthComplete >= result[ranges][0] && widthComplete <= result[ranges][1]) {
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_red', result[ranges][2] == 'red').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_pink', result[ranges][2] == 'pink').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_orange', result[ranges][2] == 'orange').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_yellow', result[ranges][2] == 'yellow').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_light_green', result[ranges][2] == 'light_green').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_green', result[ranges][2] == 'green').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_grey', result[ranges][2] == 'grey').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_blue', result[ranges][2] == 'blue').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_purple', result[ranges][2] == 'purple').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_black', result[ranges][2] == 'black').css('width', widthComplete + '%');
                            _self.$('.o_progressbar_complete').toggleClass('o_progress_brown', result[ranges][2] == 'brown').css('width', widthComplete + '%');

                            break;
                        } else if (ranges == (result.length - 1) || max_value == 0) {
                            _self.$('.o_progressbar_complete').toggleClass('progress-bar o_progress_grey', widthComplete != 0).css('width', widthComplete + '%');
                        }
                    }
                } else {
                    _self.$('.o_progress').toggleClass('o_progress_overflow', value > max_value);
                    _self.$('.o_progressbar_complete').toggleClass('o_progress_gt_fty', widthComplete > 50).css('width', widthComplete + '%');
                    _self.$('.o_progressbar_complete').toggleClass('o_progress_lt_fty', widthComplete <= 50).css('width', widthComplete + '%');
                }
            });

            if (!this.write_mode) {
                if (self.display_value === 'value') {
                    this.$('.o_progressbar_value').text(utils.human_number(value) + " / " + utils.human_number(max_value));
                } else {
                    if (self.display_value !== 'none') {
                        this.$('.o_progressbar_value').text(utils.human_number(value) + "%");
                    }
                }
            } else if (isNaN(v)) {
                this.$('.o_progressbar_value').val(this.edit_max_value ? max_value : value);
                this.$('.o_progressbar_value').focus().select();
            }
        },
    });
});