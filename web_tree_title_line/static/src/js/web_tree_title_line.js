odoo.define('web_tree_title_line.web_tree_title_line', function (require) {
// The goal of this file is to contain JS hacks related to allowing
// section on resource calendar.
"use strict";

var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var ListRenderer = require('web.ListRenderer');
var KanbanRenderer = require('web.KanbanRenderer');

var SectionListRendererFunctions = {
    /**
     * We want section to take the whole line (except handle and trash)
     * to look better and to hide the unnecessary fields.
     *
     * @override
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var isSection = record.data.is_title_line === true;

        if (isSection) {
            if (node.attrs.widget === "handle") {
                return $cell;
            } else if (node.attrs.name === "image" || node.attrs.name === "num_poste") {
                return $cell;
            } else if (node.attrs.name === "name") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                // if (this.)
                $cell.attr('colspan', nbrColumns);
            } else {
                $cell.removeClass('o_invisible_modifier');
                return $cell.addClass('o_hidden');
            }
        }

        return $cell;
    },
    /**
     * We add the o_is_{display_type} class to allow custom behaviour both in JS and CSS.
     *
     * @override
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);

        if (record.data.display_type) {
            $row.addClass('o_is_' + record.data.display_type);
        }

        return $row;
    },
    /**
     * We want to add .o_section_list_view on the table to have stronger CSS.
     *
     * @override
     * @private
     */
    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_list_table').addClass('o_section_list_view');
        });
    },
};

// for One2many
var SectionListRenderer = ListRenderer.extend(SectionListRendererFunctions);

FieldOne2Many.include({
    /**
     * We want to use our custom renderer for the list.
     *
     * @override
     */
    _render: function () {
        if (!this.view) {
            return this._super();
        }
        if (this.renderer) {
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer.updateState(this.value, {'columnInvisibleFields': this.currentColInvisibleFields});
            this.pager.updateState({ size: this.value.count });
            return $.when();
        }
        var arch = this.view.arch;
        var viewType;
        if (arch.tag === 'tree') {
            viewType = 'list';
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            this.renderer = new SectionListRenderer(this, this.value, {
                arch: arch,
                editable: this.mode === 'edit' && arch.attrs.editable,
                addCreateLine: !this.isReadonly && this.activeActions.create,
                addTrashIcon: !this.isReadonly && this.activeActions.delete,
                viewType: viewType,
                columnInvisibleFields: this.currentColInvisibleFields,
            });
        }
        if (arch.tag === 'kanban') {
            viewType = 'kanban';
            var record_options = {
                editable: false,
                deletable: false,
                read_only_mode: this.isReadonly,
            };
            this.renderer = new KanbanRenderer(this, this.value, {
                arch: arch,
                record_options: record_options,
                viewType: viewType,
            });
        }
        this.$el.addClass('o_field_x2many o_field_x2many_' + viewType);
        return this.renderer ? this.renderer.appendTo(this.$el) : this._super();
    },
});

// for classic list view
ListRenderer.include(SectionListRendererFunctions);

});
