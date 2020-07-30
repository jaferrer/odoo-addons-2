odoo.define('web_kanban_awesome_gauge.widget', function (require) {
"use strict";

var utils = require('web.utils');
var GaugeWidget = require('web_kanban_gauge.widget');


GaugeWidget.include({

    _render: function () {
        // parameters
        var max_value = this.nodeOptions.max_value || 100;
        if (this.nodeOptions.max_field) {
            max_value = this.recordData[this.nodeOptions.max_field];
        }
        var label = this.nodeOptions.label || "";
        if (this.nodeOptions.label_field) {
            label = this.recordData[this.nodeOptions.label_field];
        }
        var title = this.nodeOptions.title || this.field.string;
        // current gauge value
        var val = this.value;
        if (_.isArray(JSON.parse(val))) {
            val = JSON.parse(val);
        }
        var value = _.isArray(val) && val.length ? val[val.length-1].value : val;
        // displayed value under gauge
        var gauge_value = value;
        if (this.nodeOptions.gauge_value_field) {
            gauge_value = this.recordData[this.nodeOptions.gauge_value_field];
        }

        var degree = Math.PI/180,
            width = 150,
            height = 100,
            outerRadius = Math.min(width, height)*0.75,
            innerRadius = outerRadius*0.7,
            fontSize = height/4;

        this.$el.empty().attr('style', this.nodeOptions.style + ';position:relative; display:inline-block;');

        var arc = d3.svg.arc()
                .innerRadius(innerRadius)
                .outerRadius(outerRadius)
                .startAngle(-90*degree);

        var svg = d3.select(this.$el[0])
            .append("svg")
            .attr("width", '100%')
            .attr("height", '100%')
            .attr('viewBox','0 0 ' + width + ' ' + height )
            .attr('preserveAspectRatio','xMinYMin')
            .append("g")
            .attr("transform", "translate(" + (width/2) + "," + (height-20) + ")");

        function addText(text, fontSize, dx, dy) {
            return svg.append("text")
                .attr("text-anchor", "middle")
                .style("font-size", fontSize+'px')
                .attr("dy", dy)
                .attr("dx", dx)
                .text(text);
        }
        // top title
        // addText(title, 16, 0, -outerRadius-16).style("font-weight",'bold');

        // center value
        addText(utils.human_number(value, 1), fontSize, 0, -2).style("font-weight",'bold');

        // bottom label
        addText(0, 14, -(outerRadius+innerRadius)/2, 16);
        addText(label, 14, 0, 16);
        addText(isNaN(max_value) ? '0' : utils.human_number(max_value, 1), 14, (outerRadius+innerRadius)/2, 16);

        // chart
        svg.append("path")
            .datum({endAngle: Math.PI/2})
            .style("fill", "#e05072")
            .attr("d", arc);

        var foreground = svg.append("path")
            .datum({endAngle: -Math.PI/2})
            .style("fill", "#3ac47d")
            .attr("d", arc);

        var ratio = max_value && max_value != 0 ? value/max_value : 1;
        var hue = Math.round(ratio*120);

        foreground.transition()
            .duration(1500)
            .call(arcTween, (ratio-0.5)*Math.PI);

        function arcTween (transition, newAngle) {
            transition.attrTween("d", function(d) {
                var interpolate = d3.interpolate(d.endAngle, newAngle);
                return function (t) {
                    d.endAngle = interpolate(t);
                    return arc(d);
                };
            });
        }
    },
});

});
