openerp.document_scanner = function (instance) {
    _t = instance.web._t;
    instance.web.Sidebar.include({

        start: function () {
            this._super();
            self = this;
            this.$el.on('click', '.oe_sidebar_scan_attachment_select', function (event) {
                ids = [];
                model = '';
                if (self.getParent() === undefined){
                    ctx = self.view.ViewManager.ActionManager.action_context.context;
                    ids = ctx.active_ids;
                    model = ctx.active_model;
                } else {
                    ids = self.getParent().get_selected_ids();
                    model = self.getParent().dataset.model;
                }
                console.log(model);
                if (ids.length > 0 && model.length > 0){
                    var context = {
                        active_id: ids[0],
                        active_ids: ids,
                        active_model: model
                    };
                    new instance.web.Model('ir.attachment')
                        .call('scan', [context])
                        .then(function (data) {
                            if (data && data.error !== undefined) {
                                console.log(data);
                                alert(_t("The request has not been sent") + '\n' + data.error);
                            } else {
                                self.do_notify(_t("Scanning information"), _t("The request has been sent to the scanner :") + data.scan_name);
                            }
                        });
                }
            });
            this.$el.on('click', '.oe_sidebar_scan_attachment_select_duplex', function (event) {
                ids = [];
                model = '';
                if (self.getParent() === undefined){
                    ctx = self.view.ViewManager.ActionManager.action_context.context;
                    ids = ctx.active_ids;
                    model = ctx.active_model;
                } else {
                    ids = self.getParent().get_selected_ids();
                    model = self.getParent().dataset.model;
                }
                if (ids.length > 0 && model.length > 0){
                    var context = {
                        active_id: ids[0],
                        active_ids: ids,
                        active_model: model
                    };
                    new instance.web.Model('ir.attachment')
                        .call('scan_duplex', [context])
                        .then(function (data) {
                            if (data && data.error != undefined) {
                                console.log(data);
                                alert(_t("The request has not been sent") + '\n' + data.error);
                            } else {
                                self.do_notify(_t("Scanning information"), _t("The request has been sent to the scanner :") + data.scan_name);
                            }
                        });
                }
            });
        }
    });
};
