odoo.define('web_calendar_fixed_colors.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');
    var session = require('web.session');

    CalendarView.include({
        init: function () {
            var res = this._super.apply(this, arguments);
            this.info_fields = [];
            for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
                if (!this.fields_view.arch.children[fld].attrs.invisible) {
                    this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
                }
            }
            return res
        },

        _compute_colors: function (colors_str) {
            return _(colors_str.split(';')).chain()
                .compact()
                .map(function (color_pair) {
                    var pair = color_pair.split(':'),
                        color = pair[0],
                        expr = pair[1];
                    return [color, py.parse(py.tokenize(expr)), expr];
                }).value();
        },

        parse_colors: function () {
            if (this.fields_view.arch.attrs.colors) {
                this.colors = this._compute_colors(this.fields_view.arch.attrs.colors);
            }
            if (this.fields_view.arch.attrs.text_colors) {
                this.text_colors = this._compute_colors(this.fields_view.arch.attrs.text_colors);
            }
        },

        start: function () {
            this.parse_colors();
            return this._super();
        },

        event_data_transform: function (evt) {
            var r = this._super(evt);
            r.color = undefined;
            r.textColor = "#0d0d0d";
            var context = _.extend({}, evt, {
                uid: session.uid,
                current_date: moment().format('YYYY-MM-DD')
            });
            if (this.colors !== undefined) {
                for (var i = 0, len = this.colors.length; i < len; ++i) {
                    var pair = this.colors[i],
                        color = pair[0],
                        expression = pair[1];
                    if (py.PY_isTrue(py.evaluate(expression, context))) {
                        r.color = color;
                    }
                }
            }
            if (this.text_colors !== undefined) {
                for (var i = 0, len = this.text_colors.length; i < len; ++i) {
                    var pair = this.text_colors[i],
                        color = pair[0],
                        expression = pair[1];
                    if (py.PY_isTrue(py.evaluate(expression, context))) {
                        r.textColor = color;
                    }
                }
            }

            return r;
        }
    });
});
