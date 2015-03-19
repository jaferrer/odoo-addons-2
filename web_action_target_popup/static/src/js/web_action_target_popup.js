openerp.web_action_target_popup = function(instance){

    instance.web.ActionManager.include({

        init: function(parent) {
            this._super(parent);
            this.child_dialog = null;
            this.child_dialog_widget = null;
        },

        dialog_stop: function (reason) {
            if (this.child_dialog) {
                this.child_dialog.destroy(reason);
                this.child_dialog = null;
            }
            else {
                this._super(reason);
            }
        },

        do_action: function(action, options) {
            if (action.target === "popup") {
                action.flags = _.defaults(action.flags || {}, {
                    views_switcher : false,
                    search_view : false,
                    action_buttons : false,
                    sidebar : false,
                    pager : !_.str.startsWith(action.view_mode, 'form'),
                    display_title : false,
                    search_disable_custom_filters: action.context && action.context.search_disable_custom_filters
                });
            }
            return this._super(action, options);
        },

        ir_actions_common: function(executor, options) {
            var widget = executor.widget();
            var self = this;
            if (executor.action.target === 'popup') {
                console.log("I'm in!!");
                var pre_dialog = (this.dialog && !this.dialog.isDestroyed()) ? this.dialog : null;
                if (!pre_dialog){
                    // no previous dialog, so we call with target="new"
                    executor.action.target = 'new';
                    return this._super(executor, options);
                }
                this.child_dialog = new instance.web.Dialog(this, {
                    title: executor.action.name,
                    dialogClass: executor.klass,
                });

                // Refresh parent popup on closing and ignore options.on_close
                this.child_dialog.on_close = function(){
                    var widget = self.dialog_widget;
                    var active_view = widget.views[widget.active_view];
                    active_view.controller.reload();
                };
                this.child_dialog.on("closing", null, this.child_dialog.on_close);
                if (widget instanceof instance.web.ViewManager) {
                    _.extend(widget.flags, {
                        $buttons: this.child_dialog.$buttons,
                        footer_to_buttons: true,
                    });
                }
                this.child_dialog_widget = widget;
                this.child_dialog_widget.setParent(this.child_dialog);
                var initialized = this.child_dialog_widget.appendTo(this.child_dialog.$el);
                this.child_dialog.open();
                return initialized;
            }
            else {
                return this._super(executor, options);
            }
        },
    });
}