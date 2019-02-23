odoo.define('web_calendar_starred_domain.SidebarFilter', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var widgets = require('web_calendar.widgets');
    var _lt = core._lt;

    widgets.SidebarFilter.include({
        get_ticked_partner_ids: function (ticked_domain) {
            var promise = $.Deferred();
            new Model("res.partner")
                .query(["id"])
                .filter(ticked_domain)
                .all()
                .done(function (result) {
                    var ids = [];
                    _.each(result, function (item) {
                        console.log(item);
                        ids = ids.concat(item.id)
                    });
                    promise.resolve(ids);
                })
                .fail(function () {
                    promise.reject();
                });
            return promise;
        },
        load_favorite_list: function () {
            var self = this;
            // Untick sidebar's filters if there is an active partner in the context
            var active_partner = (this.view.dataset.context.active_model === 'res.partner');
            var ticked_domain = [];
            if (this.view.fields_view.arch.attrs['ticked_domain']) {
                ticked_domain = this.view.fields_view.arch.attrs['ticked_domain']
                ticked_domain = py.eval(ticked_domain)
            }
            if (this.view.dataset.context.hasOwnProperty('ticked_domain')) {
                ticked_domain = (this.view.dataset.context.ticked_domain);
            }
            var starred_domain = [];
            if (this.view.fields_view.arch.attrs['starred_domain']) {
                starred_domain = this.view.fields_view.arch.attrs['starred_domain']
                starred_domain = py.eval(starred_domain)
            }

            if (this.view.dataset.context.hasOwnProperty('starred_domain')) {
                starred_domain = (this.view.dataset.context.starred_domain);
            }

            ticked_domain = ticked_domain.concat(starred_domain);
            var ticked_partner_ids = [];
            return self.get_ticked_partner_ids(ticked_domain).done(function (ids) {
                ticked_partner_ids = ids;
            }).then(function () {
                session.is_bound.then(function () {
                    self.view.all_filters = {};
                    self.view.now_filter_ids = [];
                    self._add_filter(-1, _lt("Everybody's calendars"), false, false);
                    //Get my coworkers/contacts
                    if (starred_domain) {
                        return new Model("res.partner")
                            .query(["id", "name"])
                            .filter(starred_domain)
                            .all()
                            .then(function (result) {
                                var me_added = false;
                                _.each(result, function (item) {
                                    var ticked = ticked_partner_ids.length === 0 || ticked_partner_ids.indexOf(item.id) >= 0 || active_partner === true;
                                    var name = item.name;
                                    if (item.id === session.patner_id){
                                        me_added = true;
                                        name = session.name + _lt(" [Me]");
                                    }
                                    self._add_filter(item.id, name, ticked, true);
                                });
                                if (!me_added){
                                    self._add_filter(session.partner_id, session.name + _lt(" [Me]"), ticked_partner_ids.length === 0, true);
                                }

                                self.view.now_filter_ids = _.pluck(self.view.all_filters, 'value');

                                self.render();
                                self.trigger_up('reload_events')
                            });
                    } else {
                        return self.render();
                    }
                })
            });
        }
    });
});
