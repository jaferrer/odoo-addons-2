odoo.define('web_calendar_starred_domain.SidebarFilter', function (require) {
    "use strict";

    var core = require('web.core');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var widgets = require('web_calendar.widgets');
    var _lt = core._lt;

    widgets.SidebarFilter.include({

        load_favorite_list: function () {
            var favorite_model = false;
            if (this.view.fields_view.arch.attrs['favorite_model']) {
                favorite_model = this.view.fields_view.arch.attrs['favorite_model'];
            }
            if (this.view.dataset.context.hasOwnProperty('favorite_model')) {
                favorite_model = this.view.dataset.context.favorite_model;
            }
            console.log("load favorite Model" + favorite_model);
            if (!favorite_model) {
                return this._super()
            }

            var favorite_domain = this.get_favorite_domain();
            console.log("favorite_domain " + favorite_domain);
            var favorite_ticked_domain = this.get_favorite_ticked_domain();
            console.log("favorite_ticked_domain " + favorite_ticked_domain);
            favorite_domain = favorite_domain.concat(favorite_ticked_domain);
            console.log("favorite_domain2 " + favorite_domain);
            return this.load_favorite_list_with_ticked(favorite_model, favorite_domain, favorite_ticked_domain)
        },
        load_favorite_list_with_ticked: function (favorite_model, favorite_domain, favorite_ticked_domain) {
            var self = this;
            var active_partner = (this.view.dataset.context.active_model === 'res.partner');
            var ticked_partner_ids = [];
            return this.get_ticked_partner_ids(favorite_model, favorite_domain).done(function (ids) {
                ticked_partner_ids = ids;
            }).then(function () {
                session.is_bound.then(function () {
                    self.view.all_filters = {};
                    self.view.now_filter_ids = [];
                    self._add_filter(-1, _lt("Everybody's calendars"), false, false);
                    //Get my coworkers/contacts
                    if (favorite_ticked_domain) {
                        console.log("load favorite_ticked_domain " + favorite_model + " " + favorite_ticked_domain);
                        return new Model(favorite_model)
                            .query(["id", "name"])
                            .filter(favorite_ticked_domain)
                            .all()
                            .then(function (result) {
                                var me_added = false;
                                _.each(result, function (item) {
                                    var ticked = ticked_partner_ids.length === 0 || ticked_partner_ids.indexOf(item.id) >= 0;
                                    var name = item.name;
                                    if (active_partner && item.id === session.patner_id) {
                                        me_added = true;
                                        name = session.name + _lt(" [Me]");
                                        ticked = ticked || active_partner === true

                                    }
                                    self._add_filter(item.id, name, ticked, true);
                                });
                                if (!me_added && active_partner) {
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
        },
        get_ticked_partner_ids: function (favorite_model, ticked_domain) {
            console.log("get_ticked_partner_ids " + favorite_model + " " + ticked_domain);
            var promise = $.Deferred();
            new Model(favorite_model)
                .query(["id"])
                .filter(ticked_domain)
                .all()
                .done(function (result) {
                    var ids = [];
                    _.each(result, function (item) {
                        ids = ids.concat(item.id)
                    });
                    promise.resolve(ids);
                })
                .fail(function () {
                    promise.reject();
                });
            return promise;
        },
        get_favorite_domain: function () {
            var favorite_domain = [];
            if (this.view.fields_view.arch.attrs['favorite_domain']) {
                favorite_domain = py.eval(this.view.fields_view.arch.attrs['favorite_domain']);
            }
            if (this.view.dataset.context.hasOwnProperty('favorite_domain')) {
                favorite_domain = this.view.dataset.context.favorite_domain;
            }
            return favorite_domain
        },
        get_favorite_ticked_domain: function () {
            var favorite_ticked_domain = [];
            if (this.view.fields_view.arch.attrs['favorite_ticked_domain']) {
                favorite_ticked_domain = py.eval(this.view.fields_view.arch.attrs['favorite_ticked_domain']);
            }

            if (this.view.dataset.context.hasOwnProperty('favorite_ticked_domain')) {
                favorite_ticked_domain = this.view.dataset.context.favorite_ticked_domain;
            }
            return favorite_ticked_domain
        },
    });
});
