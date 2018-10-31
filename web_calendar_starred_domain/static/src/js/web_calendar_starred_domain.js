odoo.define('web_calendar_starred_domain.SidebarFilter', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var widgets = require('web_calendar.widgets');
    var _lt = core._lt;

    widgets.SidebarFilter.include({
        load_favorite_list: function () {
            var self = this;
            // Untick sidebar's filters if there is an active partner in the context
            var active_partner = (this.view.dataset.context.active_model === 'res.partner');
            var starred_domain = this.view.fields_view.arch.attrs['starred_domain'];
            return session.is_bound.then(function () {
                self.view.all_filters = {};
                self.view.now_filter_ids = [];
                self._add_filter(session.partner_id, session.name + _lt(" [Me]"), !active_partner);
                self._add_filter(-1, _lt("Everybody's calendars"), false, false);
                //Get my coworkers/contacts
                if (starred_domain) {
                    return new Model("res.partner")
                        .query(["id", "name"])
                        .filter(starred_domain)
                        .all()
                        .then(function (result) {
                            _.each(result, function (item) {
                                self._add_filter(item.id, item.name, !active_partner, true);
                            });

                            self.view.now_filter_ids = _.pluck(self.view.all_filters, 'value');

                            self.render();
                        });
                } else {
                    return self.render();
                }
            });
        }
    });
});
