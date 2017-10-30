odoo.define('web.graph_fixed', function (require) {
   "use strict";
   	
   var core = require('web.core');
   var utils = require('web.utils');
   var _t = core._t;
   var QWeb = core.qweb;
   var GraphView = require('web.GraphView');
   var GraphWidget = require('web.GraphWidget');

	GraphView.include({
        get_context: function () {
            return !this.widget ? {
                graph_mode: this.fields_view.arch.attrs.type || 'bar'
            } : {
                graph_mode: this.widget.mode,
                graph_measure: this.widget.measure,
                graph_groupbys: this.widget.groupbys
            };
        }
	});

	GraphWidget.include({
        display_graph: function () {
            if (this.to_remove) {
                nv.utils.offWindowResize(this.to_remove);
            }
            this.$el.empty();
            if (!this.data.length) {
                this.$el.append(QWeb.render('GraphView.error', {
                    title: _t("No data to display"),
                    description: _t("No data available for this chart. " +
                        "Try to add some records, or make sure that " +
                        "there is no active filter in the search bar."),
                }));
            } else {

                var chart = this['display_' + this.mode]();
                if(chart != undefined) {
                    chart.tooltip.chartContainer(this.$el[0]);
                }
            }
        }
    });
	
});

