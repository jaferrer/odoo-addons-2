odoo.define('web_calendar_fixed_colors.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');
    var session = require('web.session');

    CalendarView.include({
        view_loading: function (fv) {
            var res = this._super(fv);
            this.parse_colors();
            this.info_fields = [];
            for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
                if (!this.fields_view.arch.children[fld].attrs.invisible) {
                    this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
                }
            }
            return res
        },

        parse_colors: function () {
            if (this.fields_view.arch.attrs.colors) {
                this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain()
                    .compact()
                    .map(function (color_pair) {
                        var pair = color_pair.split(':'),
                            color = pair[0],
                            expr = pair[1];
                        return [color, py.parse(py.tokenize(expr)), expr];
                    }).value();
            }
        },

        event_data_transform: function (evt) {
            var r = this._super(evt);
            r.color = undefined;
            if (this.colors !== undefined) {
                for (var i = 0, len = this.colors.length; i < len; ++i) {
                    var context = _.extend({}, evt, {
                        uid: session.uid,
                        current_date: moment().format('YYYY-MM-DD')
                    });
                    var pair = this.colors[i],
                        color = pair[0],
                        expression = pair[1];
                    if (py.PY_isTrue(py.evaluate(expression, context))) {
                        r.color = color;
                    }
                }
            }
            return r;
        }
    });
});
