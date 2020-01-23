odoo.define('web_calendar_color_filter.web_calendar_color_filter', function (require) {
    'use strict';

    var CalendarRenderer = require('web.CalendarRenderer');
    var rpc = require('web.rpc');

    CalendarRenderer.include({

        init: function (parent, state, params) {
            this._super(parent, state, params);
            var color_field = params.arch.attrs.color;
            if (state.fields[color_field].type == 'many2one') {
                var filters = state.filters[color_field].filters;
                var filter_ids = [];
                for (var i = 0; i < filters.length; i++) {
                    filter_ids.push(filters[i].value);
                }
                rpc.query({
                    model: state.fields[color_field].relation,
                    method: 'read',
                    args: [filter_ids, ['color']],
                }).then(function (results) {
                    console.log(results)
                    for (var j = 0; j < results.length; j++) {
                        results[j].color
                        var span = $('.o_calendar_filter_items').find('div[data-value=' + results[j].id + ']').find('span.color_filter')
                        span[0].style = 'border-bottom: 4px solid ' + results[j].color + ';'
                    }
                    state.filters[color_field].filters = filters;
                })
            }
        }
    })
});