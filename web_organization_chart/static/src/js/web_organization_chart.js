var nodeTemplate = function (data) {
    data.function = data.function || '';
    data.email = data.email ? data.email + '<br/>' : '';
    return `<div class="${data.company_type}"><div class="title">${data.display_name}</div>
        <div class="content">${data.function}${data.email}</div></div>`;
};

odoo.define('web.OrganizationChart', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var field_registry = require('web.field_registry');

    var FieldOrganizationChart = AbstractField.extend({

        /**
         * @override
         */
        start: function () {
            let self = this;
            this.organization_chart = this.$el;
            this._super.apply(this, self);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        _render: function () {
            if (!this.recordData.id) {
                this._super.apply(this, self);
            }
            return this.init_organization_chart()
        },

        /**
         * Initializes the organization_chart.
         *
         * @private
         */
        init_organization_chart: function () {
            let self = this;

            let nodeId = this.recordData.id;
            this.organization_chart = this.organization_chart.empty().orgchart({
                'data': 'get_init_data?node_id=' + nodeId,
                'ajaxURL': {},
                'nodeTemplate': nodeTemplate,
                'createNode': function ($node, data) {
                    if (data.id === nodeId) {
                        $node.addClass('focused');
                    }
                    $node.unbind('click');
                    $node.on('click', function(event) {
                        event.preventDefault();
                        let partner_id = parseInt(event.currentTarget.id);
                        return self.do_action({
                            type: 'ir.actions.act_window',
                            view_type: 'form',
                            view_mode: 'form',
                            views: [[false, 'form']],
                            target: 'current',
                            res_model: 'res.partner',
                            res_id: partner_id,
                        });
                    });
                }
            });
        },
    });

    field_registry.add('organization_chart', FieldOrganizationChart);
    return FieldOrganizationChart;
});
