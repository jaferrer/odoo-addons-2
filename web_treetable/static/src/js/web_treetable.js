odoo.define('web_treetable.web_treetable', function (require) {

var ListRenderer = require('web.ListRenderer');
var FormRenderer = require('web.FormRenderer');

var registerTreetable = function() {
     $('.web_treetable > table.o_list_view').treetable({
            expandable: true,
            indent: 19
        });
     $('a.treetable-control').remove()
     $('.web_treetable > table.o_list_view').before(
         "<a href='#' class='treetable-control' onclick=\"$('.web_treetable > table.o_list_view').treetable('collapseAll');\"><i class='fa fa-fw o_button_icon fa-compress'></i></a>"
     );
     $('.web_treetable > table.o_list_view').before(
        "<a href='#' class='treetable-control' onclick=\"$('.web_treetable > table.o_list_view').treetable('expandAll');\"><i class='fa fa-fw o_button_icon fa-expand'></i></a>"
     );

     $('.web_treetable > table.o_list_view > tbody > tr').each(function(index, value) {
         if ($(value).attr('data-tt-id') && $(value).attr('data-tt-collapsed') === 'false') {
             $('.web_treetable > table.o_list_view').treetable('expandNode', $(value).attr('data-tt-id'));
         }
     })
};

var getLevel = function(numPoste) {
    return "level-" + (numPoste.split(".").length - 1)
};

ListRenderer.include({

    _renderRow: function (record) {
        var result = this._super.apply(this, arguments);

        var id, parentId, collapsed = null;
        Object.keys(record.fieldsInfo.list).forEach(function (key, index) {
            let treeField = record.fieldsInfo.list[key];
            if (!treeField.context) return;

            if (treeField.context.includes('tt-id')) {
                id = key
            } else if (treeField.context.includes('tt-parent-id')) {
                parentId = key
            } else if (treeField.context.includes('tt-collapsed')) {
                collapsed = key
            }
        });

        if (id) result.attr("data-tt-id", record.data[id]).addClass(getLevel(record.data[id]));
        if (parentId) result.attr("data-tt-parent-id", record.data[parentId]);
        if (collapsed) result.attr("data-tt-collapsed", record.data[collapsed]);
        return result;
    },

    on_attach_callback: function () {
        registerTreetable();
        return this._super.apply(this, arguments);
    }
});

// Pour la vue liste dans une vue form
FormRenderer.include({
    on_attach_callback: function () {
       registerTreetable();
       return this._super.apply(this, arguments);
    },
     _updateView: function ($newContent) {
       let result = this._super.apply(this, arguments);
       registerTreetable();
       return result;
    },
    confirmChange: function (state, id, fields, e) {
        return this._super.apply(this, arguments).then(function () {
            registerTreetable();
            return;
        });
    },
});

});