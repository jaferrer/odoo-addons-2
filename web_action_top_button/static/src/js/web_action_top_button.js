openerp.web_action_top_button = function(instance){

    instance.web.Sidebar.include({

        init: function(parent) {
            var self = this;
            this._super(parent);
            this.sections.push({ 'name' : 'buttons', 'label' : _t('Buttons'), });
            this.items['buttons'] = [];
        },

        start: function() {
            var self = this;
            this._super(this);
            this.redraw();
            this.$el.on('click','.oe_sidebar_button', function(event) {
                var section = $(this).data('section');
                var index = $(this).data('index');
                var item = self.items[section][index];
                if (item.callback) {
                    item.callback.apply(self, [item]);
                } else if (item.action) {
                    self.on_item_action_clicked(item);
                } else if (item.url) {
                    return true;
                }
                event.preventDefault();
            });
        },

        add_toolbar: function(toolbar) {
            var self = this;
            var top_items = [];
            _.each(['print','action','relate'], function(type) {
                var items = toolbar[type];
                var out_items = [];
                if (items) {
                    for (var i = 0; i < items.length; i++) {
                        var action = items[i];
                        if (action.usage === "top_button") {
                            top_items.push({
                                label: action.name,
                                action: action,
                                classname: 'oe_sidebar_buttons'
                            });
                        }
                        else {
                            out_items.push({
                                label: items[i]['name'],
                                action: items[i],
                                classname: 'oe_sidebar_' + type
                            });
                        }
                    }
                    self.add_items(type=='print' ? 'print' : 'other', out_items);
                }
            });
            self.add_items('buttons', top_items);
        },
    });
}