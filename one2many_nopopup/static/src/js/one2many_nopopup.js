openerp.one2many_nopopup = function (instance) {
'use strict';
instance.web.form.One2ManyListView = instance.web.form.One2ManyListView.extend({
    do_activate_record: function(index, id) {
    var self = this;
    if (self.o2m.options.nopopup == 1) {
        var context = self.o2m.build_context()
        var model_obj = new instance.web.Model(this.dataset.model);
        model_obj.call('get_formview_action', [id, context]).then(function(action){
            self.do_action(action);
        });
        return false;
    } else {
        return self._super.apply(self, arguments);
    }
}
});
};
