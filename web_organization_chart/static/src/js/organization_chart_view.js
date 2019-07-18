// Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as
//    published by the Free Software Foundation, either version 3 of the
//    License, or (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.

odoo.define('web_organization_chart.OrganizationChartView', function (require) {
    "use strict";

    var core = require('web.core');
    var view_registry = require('web.view_registry');
    var AbstractView = require('web.AbstractView');
    var OrganizationChartRenderer = require('web_organization_chart.OrganizationChartRenderer');
    var OrganizationChartController = require('web_organization_chart.OrganizationChartController');
    var OrganizationChartModel = require('web_organization_chart.OrganizationChartModel');

    var _lt = core._lt;
    var _t = core._t;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    var OrganizationChartView = AbstractView.extend({
        display_name: _lt('Organization Chart'),
        icon: 'fa-sitemap',
        jsLibs: ['/web_organization_chart/static/src/js/jquery_orgchart.js'],
        cssLibs: ['/web_organization_chart/static/src/css/jquery_orgchart.css'],
        config: {
            Model: OrganizationChartModel,
            Controller: OrganizationChartController,
            Renderer: OrganizationChartRenderer,
        },

        /**
         * @constructor
         * @override
         */
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            this.arch = viewInfo.arch;
            this.fields = viewInfo.fields;
            this.modelName = this.controllerParams.modelName;
            this.action = params.action;

            var fieldNames = this.fields.display_name ? ['display_name'] : [];

            var archFieldNames = _.map(_.filter(this.arch.children, function (item) {
                return item.tag === 'field';
            }), function (item) {
                return item.attrs.name;
            });

            fieldNames = _.union(
                fieldNames,
                archFieldNames
            );

            if (!viewInfo.field_parent || fieldNames.indexOf(viewInfo.field_parent) < 0) {
               throw new Error(_t("Parent ID not specified in the field_parent XML attribute or not found ."));
            }

            if (isNullOrUndef(this.arch.attrs.event_open_popup) || !_.str.toBoolElse(this.arch.attrs.event_open_popup, true)) {
                this.open_popup_action = false;
            } else {
                this.open_popup_action = this.arch.attrs.event_open_popup;
            }

            this.rendererParams.model = this.modelName;
            this.rendererParams.options = this.options;
            this.rendererParams.permissions = this.permissions;
            this.rendererParams.colors = this.colors;
            this.rendererParams.fieldParent = viewInfo.field_parent;
            this.rendererParams.fieldNames = fieldNames;
            this.rendererParams.view = this;
            this.loadParams.modelName = this.modelName;
            this.loadParams.fieldNames = fieldNames;
            this.controllerParams.actionContext = this.action.context;
            this.controllerParams.open_popup_action = this.open_popup_action;
            return this;
        },

    });

    view_registry.add('organization_chart', OrganizationChartView);
    return OrganizationChartView;
});
