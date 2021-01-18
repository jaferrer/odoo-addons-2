openerp.calendar_monday_as_first_day_of_the_week = function (instance) {
'use strict';
instance.web.DateTimeWidget = instance.web.DateTimeWidget.extend({
    start: function() {
        Date.CultureInfo.firstDayOfWeek = 1;
        this._super();
    },
});
instance.web.DateWidget = instance.web.DateWidget.extend({
    start: function() {
        Date.CultureInfo.firstDayOfWeek = 1;
        this._super();
    },
});
};
