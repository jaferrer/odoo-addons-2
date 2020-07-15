odoo.define('web_form_listview_sticky_header.StickyHeaderFormRenderer', function (require) {
'use strict';

var FormRenderer = require('web.FormRenderer');

var StickyHeaderFormRenderer = FormRenderer.include({

    on_attach_callback: function () {
        var listViews = '.o_field_one2many table.o_list_view';
        var contentArea = '.o_content';
        var offset = $('.o_form_statusbar').outerHeight();

        $(listViews).stickyTableHeaders({
            scrollableArea: $(contentArea),
            fixedOffset: offset
        });

        return this._super.apply(this, arguments);
    },
});

return StickyHeaderFormRenderer;
});