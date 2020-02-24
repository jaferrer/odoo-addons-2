odoo.define('web_treetable.web_treetable', function (require) {

var ListRenderer = require('web.ListRenderer');
var FormRenderer = require('web.FormRenderer');

let treetable = '.web_treetable > table.o_list_view';

let registerTreetable = function (isListView=true) {

    if (!$(treetable).length) {
        return;
    }

    // Initiate the treetable
    $(treetable + ' span.indenter').remove();
    $(treetable).treetable({
        expandable: true,
        indent: 19,
        column: isListView ? 1 : 0
    }, true);

    // Add controls
    $('a.treetable-control').remove();
    $(treetable).before("<a href='#' class='treetable-control' onclick=\"$('.web_treetable > table.o_list_view').treetable('collapseAll');\"><i class='fa fa-fw o_button_icon fa-compress'></i></a>");
    $(treetable).before("<a href='#' class='treetable-control' onclick=\"$('.web_treetable > table.o_list_view').treetable('expandAll');\"><i class='fa fa-fw o_button_icon fa-expand'></i></a>");

    // Expand rows
    $(treetable + ' > tbody > tr.o_data_row').each(function (index, value) {
        if (Number.isInteger(parseInt($(value).attr('data-tt-id'))) && $(value).attr('data-tt-collapsed') === 'false') {
            $(treetable).treetable('expandNode', $(value).attr('data-tt-id'));
        }
    });

    // Sort update events
    $(treetable).on("sortupdate", function (event, ui) {
        let itemParent = ui.item.attr('data-tt-parent-id');
        let nextParent = ui.item.next().attr('data-tt-parent-id');
        let prevParent = ui.item.prev().attr('data-tt-parent-id');
        if (itemParent !== nextParent && itemParent !== prevParent) {
            $(event.target).sortable("cancel");
        }
    });
};

let getLevel = function (numPoste) {
    if (numPoste) {
        return "level-" + (numPoste.split(".").length - 1);
    } else {
        return "level-0";
    }
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

        if (id && record.data[id]) result.attr("data-tt-id", record.data[id]).addClass(getLevel(record.data[id]));
        if (parentId && record.data[parentId]) result.attr("data-tt-parent-id", record.data[parentId]);
        if (collapsed) result.attr("data-tt-collapsed", record.data[collapsed]);
        return result;
    },

    unselectRow: function () {
        return this._super.apply(this, arguments).then(function () {
            if (arguments.length === 1) {
                registerTreetable();
            }
        });
    },

    on_attach_callback: function () {
        // $('.o_cp_searchview').css('visibility', 'hidden');
        // $('.o_cp_right').css('visibility', 'hidden');
        registerTreetable();
        return this._super.apply(this, arguments);
    }
});

// Pour la vue liste dans une vue form
FormRenderer.include({
    on_attach_callback: function () {
        registerTreetable(false);
        return this._super.apply(this, arguments);
    },
    _updateView: function ($newContent) {
        let result = this._super.apply(this, arguments);
        registerTreetable(false);
        return result;
    },
    confirmChange: function (state, id, fields, e) {
        return this._super.apply(this, arguments).then(function () {
            registerTreetable(false);
        });
    },
});

});