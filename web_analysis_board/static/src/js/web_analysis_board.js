odoo.define('web_analysis_board.AnalysisBoard', function (require) {
    "use strict";

    var core = require('web.core');
    var form_common = require('web.form_common');
    var Model = require('web.DataModel');
    var time = require('web.time');
    var View = require('web.View');
    var session = require('web.session');
    var formats = require('web.formats');
    var utils = require('web.utils');
    var FormRenderingEngine = require('web.FormRenderingEngine');

    var _t = core._t;
    var _lt = core._lt;

    var AnalysisBoard = View.extend({
        className: "o_analysis_board_widget",
        display_name: _lt('Analysis Board'),
        icon: 'fa-line-chart',
        readonly: true,
        searchable: true,
        actual_mode: "view",

        init: function (parent, dataset, view_id, options) {
            this.rendering_engine = new FormRenderingEngine(this);
            this.tags_registry = core.form_tag_registry;
            this.fields_registry = core.form_widget_registry;
            this.aggregates = {};
            this.formulas = {};
            var res = this._super.apply(this, arguments);
            return res
        },

        start: function () {
            this.rendering_engine.set_widgets_registry(this.widgets_registry);
            this.rendering_engine.set_tags_registry(this.tags_registry);
            this.rendering_engine.set_fields_registry(this.fields_registry);
            this.rendering_engine.set_fields_view(this.fields_view);
            this.rendering_engine.render_to(this.$el);
            return this._super();
        },

        do_search: function (domains, contexts, group_bys) {
            var self = this;
            return $.when(this.has_been_loaded).then(function () {
                var fields = _.pluck(_.values(self.aggregates), 'field');
                var model = new Model(self.dataset.model);
                return model
                    .call('read_aggregates', [domains, self.aggregates], {})
                    .then(function (data) {
                        _.each(_.keys(data), function (k) {
                            self.aggregates[k].value = data[k];
                            _.each(_.values(self.aggregates), function (agg) {
                                self.rendering_engine.refresh_aggregate_value(agg);
                            });
                        });
                    });
            })
        },
    });

    FormRenderingEngine.include({

        _stat_info: function (node) {
            var go;
            if (node.attributes.group_operator) {
                go = node.attributes.group_operator.value;
            } else {
                go = this.fvg.fields[node.attributes.field.value].group_operator;
            }
            var typ = this.fvg.fields[node.attributes.field.value].type;
            var rt = typ;
            if (typ === "many2one") {
                rt = 'integer'
            }
            return {
                widget: node.attributes.widget ? node.attributes.widget.value : "",
                domain: node.attributes.domain ? node.attributes.domain.value : "[]",
                field: node.attributes.field.value,
                group_operator: go,
                name: node.attributes.name.value,
                realType: rt,
                type: typ,
                string: node.attributes.string ? node.attributes.string.value : node.attributes.field.value,
            }
        },

        _renderLabel: function (node) {
            var text = node.attributes.name.value;
            if ('string' in node.attributes) { // allow empty string
                text = node.attributes.string.value;
            }
            return $('<label>', {text: text});
        },

        _renderStatistic: function (node) {
            // else {
            //
            //     // instantiate a widget to render the value if there is no formatter
            //     $value = this._renderFieldWidget(node, this.state).addClass('o_value');
            //     $el.append($value);
            // }
            //
            // // customize border left
            // if (variation) {
            //     if (variation.signClass === ' o_positive') {
            //         $el.addClass('border-success');
            //     } else if (variation.signClass === ' o_negative') {
            //         $el.addClass('border-danger');
            //     }
            // }
            //
            // this._registerModifiers(node, this.state, $el);
            // if (config.debug || node.attributes.help) {
            //     this._addStatisticTooltip($el, node);
            // }
            return $el;
        },

        refresh_aggregate_value: function (agg) {
            if (agg.widget === '') {
                // use a formatter to render the value if there exists one for the
                // specified widget attribute, or there is no widget attribute
                var fieldValue = this.view.aggregates[agg.name].value;
                var f_data = _.clone(agg);
                f_data.type = f_data.realType;
                console.log(f_data.type, agg.type);
                fieldValue = isNaN(fieldValue) ? '-' : formats.format_value(fieldValue, f_data);
                this.view.$el.find("div[name='" + agg.name + "'] > div.o_value").replaceWith($('<div>', {class: 'o_value'}).html(fieldValue));
            }
        },

        process_aggregate: function ($aggregate) {
            var self = this;
            var node = $aggregate[0];
            var agg_data = this._stat_info(node);
            this.view.aggregates[agg_data.name] = agg_data;

            var $label = this._renderLabel(node);
            var $el = $('<div>')
                .attr('name', node.attributes.name.value)
                .append($label);
            var $value;
            var valueLabel = agg_data.string ? (' ' + agg_data.string) : '';
            if (agg_data.widget === '') {
                $value = $('<div>', {class: 'o_value'}).html('-' + valueLabel);
                $el.append($value);
            }
            //  else {
            //     // instantiate a widget to render the value if there is no formatter
            //     var widget = this.fields_registry.get(agg_data.widget);
            //     console.log(widget, this.fields_registry);
            //     var w = new (widget)(self.view, utils.xml_to_json($aggregate[0]));
            //     $el.append(w);
            // }
            $aggregate.replaceWith($el);
            return $el
        },

        process_formula: function ($formula) {
            console.log("Formula", $formula)
            return $formula
        }
    });

    core.view_registry.add('analysis', AnalysisBoard);
    return AnalysisBoard;

});