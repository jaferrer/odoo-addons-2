odoo.define('web_treetable.web_treetable_oa', function (require) {

var RelationalFields = require('web.relational_fields');

RelationalFields.FieldOne2Many.include({

    _onAddRecord: function (ev) {
        var self = this;
        // we don't want interference with the components upstream.
        ev.stopPropagation();

        let isEditableForm = !this.el.classList.contains('editable-form');

        if ((this.editable && isEditableForm) || ev.data.forceEditableLine) {
            if (!this.activeActions.create) {
                if (ev.data.onFail) {
                    ev.data.onFail();
                }
            } else if (!this.creatingRecord) {
                this.creatingRecord = true;
                this.trigger_up('edited_list', { id: this.value.id });
                this._setValue({
                    operation: 'CREATE',
                    position: this.editable,
                }).always(function () {
                    self.creatingRecord = false;
                });
            }
        } else {
            this._openFormDialog({
                on_saved: function (record) {
                    self._setValue({ operation: 'ADD', id: record.id });
                },
            });
        }
    },
});

});