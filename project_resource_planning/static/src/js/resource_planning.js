odoo.define('resource_planning.Planning', function (require) {
    "use strict";

    const core = require('web.core');
    const TimelineView = require('web_timeline2.TimelineView');

    let PlanningView = TimelineView.extend({
        display_name: core._lt('Planning'),
        icon: 'fa-hourglass-o',
    });
    core.view_registry.add('planning', PlanningView);
    return PlanningView
});