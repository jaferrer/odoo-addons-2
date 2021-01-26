odoo.define('web_tree_view_button.EditableListRenderer', function (require) {
"use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
      _renderHeaderCell: function (node) {
            const $th = this._super.apply(this, arguments);
            if (node.attrs.class && node.attrs.class.includes('title-tree-button')){
                $th.text(node.attrs.title);
            }
            return $th;
        },
    });
});