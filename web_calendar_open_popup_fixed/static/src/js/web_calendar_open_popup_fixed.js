odoo.define('web_calendar_open_popup_fixed.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');
    var QuickCreate = require('web_calendar.widgets.QuickCreate');

    var form_common = require('web.form_common');

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    QuickCreate.include({

        start: function (action_id) {
            var self = this;

            if (this.options.disable_quick_create) {
                this.slow_create(null, action_id);
                return;
            }
            this.on('added', this, function() {
                self.close();
            });

            this.$input = this.$('input').keyup(function enterHandler (e) {
                if(e.keyCode === $.ui.keyCode.ENTER) {
                    self.$input.off('keyup', enterHandler);
                    if (!self.quick_add()){
                        self.$input.on('keyup', enterHandler);
                    }
                } else if (e.keyCode === $.ui.keyCode.ESCAPE && self._buttons) {
                    self.close();
                }
            });

            return this._super();
        },

        slow_create: function(_data, action_id) {
            //if all day, we could reset time to display 00:00:00

            var self = this;
            var def = $.Deferred();
            var defaults = {};
            var created = false;
            var action = action_id;

            _.each($.extend({}, this.data_template, _data), function(val, field_name) {
                defaults['default_' + field_name] = val;
            });

            var pop = new form_common.FormViewDialog(this, {
                res_model: this.dataset.model,
                context: this.dataset.get_context(defaults),
                title: this.get_title(),
                disable_multiple_selection: true,
                view_id: +action,
                // Ensuring we use ``self.dataset`` and DO NOT create a new one.
                create_function: function(data, options) {
                    return self.dataset.create(data, options).fail(function (r) {
                       if (!r.data.message) { //else manage by openerp
                            throw new Error(r);
                       }
                    });
                },
                read_function: function() {
                    return self.dataset.read_ids.apply(self.dataset, arguments).fail(function (r) {
                        if (!r.data.message) { //else manage by openerp
                            throw new Error(r);
                        }
                    });
                }
            }).open();
            pop.on('closed', self, function() {
                if (def.state() === "pending") {
                    def.resolve();
                }
            });
            pop.on('create_completed', self, function() {
                created = true;
                self.trigger('slowadded');
            });
            def.then(function() {
                if (created) {
                    var parent = self.getParent();
                    parent.$calendar.fullCalendar('refetchEvents');
                }
                self.close();
                self.trigger("closed");
            });
            return def;
        }
    });

    CalendarView.include({
        open_quick_create: function(data_template) {
            if (this.fields_view.arch.attrs.create == 'false'){
                return false
            }
            if (!isNullOrUndef(this.quick)) {
                return this.quick.close();
            }
            var QuickCreate = this.get_quick_create_class();

            this.options.disable_quick_create =  this.options.disable_quick_create || !this.quick_add_pop;
            this.quick = new QuickCreate(this, this.dataset, true, this.options, data_template);
            this.quick.on('added', this, this.quick_created)
                    .on('slowadded', this, this.slow_created)
                    .on('closed', this, function() {
                        delete this.quick;
                        this.$calendar.fullCalendar('unselect');
                    });

            if(!this.options.disable_quick_create) {
                this.quick.open();
                this.quick.focus();
            } else {
                this.quick.start(this.open_popup_action);
            }
        }
    })
});
