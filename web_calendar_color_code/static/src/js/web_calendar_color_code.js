odoo.define('web_calendar_color_code.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');
    var widgets = require('web_calendar.widgets');
    var Model = require('web.DataModel');
    var session = require('web.session');

    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    widgets.SidebarFilter.include({
        init: function () {
            this._super.apply(this, arguments);
        },
        render: function() {
            var self = this;
            var filters = _.filter(this.view.get_all_filters_ordered(), function(filter) {
                return _.contains(self.view.now_filter_ids, filter.value);
            });
            this.$('.o_calendar_contacts').html(QWeb.render('CalendarView.sidebar.contacts.color', { filters: filters }));
        },
        on_add_filter: function() {
            var self = this;
            var defs = [];
            _.each(this.m2o.display_value, (element, index) => {
                if (session.partner_id !== index) {
                    defs.push(this.ds_contacts.call("create", [{'partner_id': index}]).then((result) => {
                        console.log(result);
                        this.fetch_favorite_list([['id', '=', parseInt(result)]], () =>{
                            this.reload();
                        });
                    }));
                }
            });

            return $.when.apply(null, defs).then(this.reload.bind(this));
        },
        load_favorite_list: function () {
            if (!this.view.color_code_field) {
                return this._super(arguments);
            }
            // Untick sidebar's filters if there is an active partner in the context
            var active_partner = (this.view.dataset.context.active_model === 'res.partner');
            return session.is_bound.then(() => {
                this.view.all_filters = {};
                this.view.now_filter_ids = [];
                this._add_filter(session.partner_id, session.name + _lt(" [Me]"), !active_partner);
                this._add_filter(-1, _lt("Everybody's calendars"), false, false);
                //Get my coworkers/contacts
                return this.fetch_favorite_list([["user_id", "=", session.uid]], () => {
                    this.view.now_filter_ids = _.pluck(this.view.all_filters, 'value');
                    this.render();
                })
            });
        },

        fetch_favorite_list: function(domain, on_load_call_back){
            var active_partner = (this.view.dataset.context.active_model === 'res.partner');
            return new Model('calendar.contacts').query(["partner_id", this.view.color_code_field])
                .filter(domain)
                .all()
                .then(result => {
                    result.forEach(item => {
                        console.log(item);
                        this._add_filter(item.partner_id[0], item.partner_id[1], !active_partner, true);
                        if (item[this.view.color_code_field]){
                            this.view.all_filters[item.partner_id[0]].color_code =  item[this.view.color_code_field]//Add color code
                        }
                    });
                    if (on_load_call_back){
                        on_load_call_back.bind(this).apply();
                    }
                });
        }
    });

    CalendarView.include({
        init: function () {
            this._super.apply(this, arguments);
            var attrs = this.fields_view.arch.attrs;
            this.color_code_field = attrs.color_code;
        },
        event_data_transform: function (evt) {
            var r = this._super(evt);

            var color_code = evt[this.color_code_field];
            if (color_code !== undefined) {
                r.color = color_code;
            }
            return r;
        }
    });
});
