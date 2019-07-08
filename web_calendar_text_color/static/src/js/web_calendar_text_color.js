odoo.define('web_calendar_text_color.CalendarView', function (require) {
    "use strict";

    var session = require('web.session');
    var CalendarView = require('web_calendar.CalendarView');

    CalendarView.include({
        parse_text_colors: function () {
            if (this.fields_view.arch.attrs.text_colors) {
                this.text_colors = _(this.fields_view.arch.attrs.text_colors.split(';')).chain()
                    .compact()
                    .map(function (color_pair) {
                        var pair = color_pair.split(':'),
                            color = pair[0],
                            expr = pair[1];
                        return [color, py.parse(py.tokenize(expr)), expr];
                    }).value();
            }
        },

        start: function () {
            this.parse_text_colors();
            return this._super();
        },

        event_data_transform: function (evt) {
            var res = this._super(evt);
            if (this.text_colors !== undefined) {
                for (var i = 0, len = this.text_colors.length; i < len; ++i) {
                    var context = _.extend({}, evt, {
                        uid: session.uid,
                        current_date: moment().format('YYYY-MM-DD')
                    });
                    var pair = this.text_colors[i],
                        color = pair[0],
                        expression = pair[1];
                    if (py.PY_isTrue(py.evaluate(expression, context))) {
                        res.textColor = color;
                    }
                }
            }
            return res;
        }
    });
});
