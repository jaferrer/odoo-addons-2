odoo.define('resource_planning.Planning', function (require) {
    "use strict";

    const core = require('web.core');
    const TimelineView = require('web_timeline2.TimelineView');

    let PlanningView = TimelineView.extend({
        display_name: core._lt('Planning'),
        icon: 'fa-hourglass-o',
        init: function (parent, dataset, view_id, options) {
            const result = this._super.apply(this, arguments);
            this.ViewManager.on('switch_mode', this, (n_mode) => {
                if (n_mode === "planning") {
                    this.timeline.redraw()
                }
            });
            return result;
        },
        _get_option_timeline: function () {
            const options = this._super.apply(this, arguments);
            options.format = {
                minorLabels: function(date, scale, step){
                    if(date.isSame(moment(date).startOf('week'))){
                        return date.format('[S]ww');
                    }
                    return date.format('ddd D');
                },
            }
            return options;
        }

    });
    core.view_registry.add('planning', PlanningView);
    return PlanningView
});