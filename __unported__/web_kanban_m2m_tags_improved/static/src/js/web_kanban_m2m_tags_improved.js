odoo.define('web.kanban_m2m_tags_improved', function (require) {
    "use strict";

    var core = require('web.core');
    var utils = require('web.utils');
    var data = require('web.data');
    var _t = core._t;
    var QWeb = core.qweb;
//   var _ = core._t;
    var KanbanView = require("web_kanban.KanbanView");
    var FieldMany2ManyTags = require("web.form_relational").FieldMany2ManyTags;

    KanbanView.include({
        postprocess_m2m_tags: function (records) {
            var self = this;
            if (!this.many2manys.length) {
                return;
            }
            var relations = {};
            records = records ? (records instanceof Array ? records : [records]) :
                this.grouped ? Array.prototype.concat.apply([], _.pluck(this.widgets, 'records')) :
                    this.widgets;

            records.forEach(function (record) {
                self.many2manys.forEach(function (name) {
                    var field = record.record[name];
                    var $el = record.$('.oe_form_field.o_form_field_many2manytags[name=' + name + ']');
                    // fields declared in the kanban view may not be used directly
                    // in the template declaration, for example fields for which the
                    // raw value is used -> $el[0] is undefined, leading to errors
                    // in the following process. Preventing to add push the id here
                    // prevents to make unnecessary calls to name_get
                    if (!$el[0]) {
                        return;
                    }
                    if (!relations[field.relation]) {
                        relations[field.relation] = {ids: [], elements: {}, context: self.m2m_context[name]};
                    }
                    var rel = relations[field.relation];
                    field.raw_value.forEach(function (id) {
                        rel.ids.push(id);
                        if (!rel.elements[id]) {
                            rel.elements[id] = [];
                        }
                        rel.elements[id].push($el[0]);
                    });
                });
            });
            _.each(relations, function (rel, rel_name) {
                var dataset = new data.DataSetSearch(self, rel_name, self.dataset.get_context(rel.context));
                dataset.read_ids(_.uniq(rel.ids), ['name', 'color']).done(function (result) {
                    result.forEach(function (record) {
                        // Does not display the tag if color = 0
                        //if (record.color){
                        var $tag = $('<span>' + record.name + '</span>')
                            .addClass('badge o_tag o_tag_color_' + record.color)
                            .attr('title', _.str.escapeHTML(record.name))
                            .attr('style', 'width:auto;height:auto;');
                        $(rel.elements[record.id]).append($tag);
                        //}
                    });
                    // we use boostrap tooltips for better and faster display
                    self.$('span.o_tag').tooltip({delay: {'show': 50}});
                });
            });
        }
    });

    FieldMany2ManyTags.include({
        open_color_picker: function (ev) {
            this.mutex.exec(function () {
                if (this.fields.color) {
                    this.$color_picker = $(QWeb.render('FieldMany2ManyTag.colorpicker_improved', {
                        'widget': this,
                        'tag_id': $(ev.currentTarget).data('id'),
                    }));

                    $(ev.currentTarget).append(this.$color_picker);
                    this.$color_picker.dropdown('toggle');
                    this.$color_picker.attr("tabindex", 1).focus();
                }
            }.bind(this));
        }
    });
});

