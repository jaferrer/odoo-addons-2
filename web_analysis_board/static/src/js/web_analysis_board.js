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
    var data_manager = require('web.data_manager');

    var _t = core._t;
    var _lt = core._lt;

    var AnalysisBoard = View.extend({
        className: "o_analysis_board_widget",
        template: "AnalysisBoard",
        display_name: _lt('Analysis Board'),
        icon: 'fa-line-chart',

        init: function (parent, dataset, view_id, options) {
            this.rendering_engine = new AnalysisRenderingEngine(this);
            this.tags_registry = core.form_tag_registry;
            this.fields_registry = core.form_widget_registry;
            this.statistics = {};
            this.subViews = {};
            this.subViewsLoaded = {};
            this.has_been_loaded = $.Deferred();
            console.log('init')
            return this._super.apply(this, arguments);
        },

        start: function () {
            console.log('start')
            var self = this;
            this.rendering_engine.set_widgets_registry(this.widgets_registry);
            this.rendering_engine.set_tags_registry(this.tags_registry);
            this.rendering_engine.set_fields_registry(this.fields_registry);
            this.rendering_engine.set_fields_view(this.fields_view);
            console.log('about to render')
            this.rendering_engine.render_to(this.$el);
            console.log("end start")
            var subs = _.values(this.subViewsLoaded);
            console.log(subs);
            $.when.apply($, subs).done(function () {
                console.log("all resolved");
                self.has_been_loaded.resolve();
            });
            var res = this._super();
            console.log("exit start")
            return res
        },

        do_search: function (domains, contexts, group_bys) {
            console.log('do_search')
            var self = this;
            return $.when(this.has_been_loaded).then(function () {
                _.each(self.subViews, function (sv) {
                    console.log('toto')
                    sv.do_search(domains, contexts, group_bys)
                });
                var model = new Model(self.dataset.model);
                return model
                    .call('read_aggregates', [domains, self.statistics], {})
                    .then(function (data) {
                        _.each(_.keys(data), function (k) {
                            self.statistics[k].value = data[k];
                            _.each(_.values(self.statistics), function (agg) {
                                self.rendering_engine.refresh_statistics_value(agg);
                            });
                        });
                    });
            })
        },

        do_show: function () {
            console.log('do_show')
            _.each(this.subViews, function (sv) {
                console.log(">", sv)
                sv.do_show();
            });
            this.do_push_state({});
            return this._super();
        },

    });

    var AnalysisRenderingEngine = FormRenderingEngine.extend({

        _stat_info: function (node) {
            var go;
            var typ;
            var rt = 'float';
            if (node.attributes.field) {
                if (node.attributes.group_operator) {
                    go = node.attributes.group_operator.value;
                } else {
                    go = this.fvg.fields[node.attributes.field.value].group_operator;
                }
                typ = this.fvg.fields[node.attributes.field.value].type;
                rt = typ;
                if (typ === "many2one") {
                    rt = 'integer'
                }
            }
            return {
                widget: node.attributes.widget ? node.attributes.widget.value : "",
                domain: node.attributes.domain ? node.attributes.domain.value : "[]",
                field: node.attributes.field ? node.attributes.field.value : null,
                group_operator: go,
                name: node.attributes.name.value,
                realType: rt,
                type: typ,
                string: node.attributes.string ? node.attributes.string.value : node.attributes.field.value,
                formula: node.attributes.value ? node.attributes.value.value : "",
                stat_type: node.attributes.value ? 'formula' : 'aggregate'
            }
        },

        _renderLabel: function (node) {
            var text = node.attributes.name.value;
            if ('string' in node.attributes) { // allow empty string
                text = node.attributes.string.value;
            }
            return $('<label>', {text: text});
        },

        refresh_statistics_value: function (stat) {
            var fieldValue = this.view.statistics[stat.name].value;
            var f_data = _.clone(stat);
            f_data.type = f_data.realType;
            fieldValue = isNaN(fieldValue) ? '-' : formats.format_value(fieldValue, f_data);
            this.view.$el.find("div[name='" + stat.name + "'] > div.o_value").replaceWith($('<div>', {class: 'o_value'}).html(fieldValue));
        },

        process_aggregate: function ($aggregate) {
            return this._process_statistic($aggregate)
        },

        process_formula: function ($formula) {
            return this._process_statistic($formula)
        },

        _process_statistic: function ($stat) {
            var node = $stat[0];
            var agg_data = this._stat_info(node);
            this.view.statistics[agg_data.name] = agg_data;

            var $label = this._renderLabel(node);
            var $el = $('<div>')
                .attr('name', node.attributes.name.value)
                .addClass('o_' + agg_data.stat_type)
                .append($label);
            var $value = $('<div>', {class: 'o_value'}).html('-');
            $el.append($value);
            $stat.replaceWith($el);
            return $el
        },

        process_view: function ($view) {
            console.log("view", $view.name, this);
            console.log(core.view_registry);
            console.log('datamanager', data_manager);
            var self = this;
            var node = $view[0];
            var viewType = node.attributes.type.value;
            var SubView = core.view_registry.get(viewType);
            var $div = $('<div>', {class: 'o_subview', type: viewType});
            var view_id = node.attributes.view_id ? Number(node.attributes.view_id.value) : null;
            self.view.subViews[view_id] = null;
            self.view.subViewsLoaded[view_id] = $.Deferred();

            data_manager.load_fields_view(this.view.dataset, view_id, viewType, false).then(function (data) {
                var subView = new SubView(self.view, self.view.dataset, data);
                self.view.subViews[view_id] = subView;
                console.log("loaded", subView);
                $div.append(subView.$el);
                $view.replaceWith($div);
                return subView.willStart().then(function () {
                    return subView.start();
                }).then(function() {
                    self.view.subViewsLoaded[view_id].resolve();
                });
            });
            return $div;
        }

    });

    core.view_registry.add('analysis', AnalysisBoard);
    return AnalysisBoard;

})
;