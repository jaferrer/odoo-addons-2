openerp.web_graph_update = function(instance) {
	
	var _lt = openerp.web._lt;
	var _t = openerp.web._t;
	
	instance.web_graph.Graph.include({
		
	    events: {
	        'click .graph_mode_selection label' : 'mode_selection',
	        'click .graph_measure_selection li' : 'measure_selection',
	        'click .graph_options_selection label' : 'option_selection',
	        'click .graph_heatmap label' : 'heatmap_mode_selection',
	        'click .web_graph_click' : 'header_cell_clicked',
	        'click a.field-selection' : 'field_selection',
	        'click thead th.oe_sortable[data-id]': 'sort_by_column'
	    },
		
		draw_measure_row: function (measure_row) {
	        var $row = $('<tr>').append('<th>');
	        var self=this;
	        _.each(measure_row, function (cell,index) {
	        	_.each(self.measure_list,function(item){
	        	    console.log(index);
	        		if(item.string==cell.text) {
		        		var $cell = $('<th>').addClass('measure_row').addClass('oe_sortable').attr('data-id',
		        				(self.pivot.sort!=null && self.pivot.sort[0].indexOf(item.field)>=0 && self.pivot.sort[0].indexOf('-') == -1)?
		        						"-"+item.field:item.field).append("<div>"+cell.text+"</div>");
			            if (cell.is_bold) {$cell.css('font-weight', 'bold');}
			            if (self.pivot.sort!=null && self.pivot.sort[0].indexOf(item.field)>=0 && index == self.pivot.index_sort) {
			            	$cell.addClass((self.pivot.sort[0].indexOf('-') == -1)?"sortup":"sortdown");
			            }
			            $row.append($cell);
	        		}
	        	}) 
	        });
	        this.$thead.append($row);
	    },
	 
	    sort_by_column: function (e) {
            e.stopPropagation();
            var $column = $(e.currentTarget);
            var col_name = $column.data('id');
            this.pivot.index_sort = $column[0].cellIndex - 1;
            sort=[]
            _.each(this.pivot.cols.groupby, function (col) {
				sort.push(col.field);
            });

            this.pivot.sort=[col_name];
            this.pivot.sort_group=sort;
            this.pivot.update_data().then(this.proxy('display_data'));
        },

    draw_rows: function (rows, doc_fragment, frozen_rows) {
        var rows_length = rows.length,
            $tbody = $('<tbody>');

        doc_fragment.append($tbody);
        var self = this;

        if(this.pivot.index_sort !=null) {

            rows.sort(function compare(a, b) {
                comp = (self.pivot.sort[0].indexOf('-') == -1)?-1:1;
                var genreA = parseFloat(a.cells[self.pivot.index_sort].value.toUpperCase().replace(",", ".").replace(/\s/g, ""));
                var genreB = parseFloat(b.cells[self.pivot.index_sort].value.toUpperCase().replace(",", ".").replace(/\s/g, ""));
                if (a.cells[self.pivot.index_sort].value == "") {
                    genreA = null;
                }
                if (b.cells[self.pivot.index_sort].value == "") {
                    genreB = null;
                }
                var comparison = 0;
                if ((genreA != null && genreB == null) || (genreA != null && genreB != null && genreA > genreB)) {
                    comparison = -1*comp;
                } else if ((genreA == null && genreB != null) || (genreA != null && genreB != null && genreA < genreB)) {
                    comparison = 1*comp;
                }
                return comparison;
            });
        }
        for (var i = 0; i < rows_length; i++) {
            $tbody.append(this.draw_row(rows[i], frozen_rows));
        }
    }
	    
	});

    instance.web_graph.PivotTable.include({
    	
    	sort : null,
		sort_group: [],
        index_sort:null,
    	
    	get_groups: function (groupbys, fields, domain) {
            var self = this;
            var result = this.model.query(_.without(fields, '__count'));
            /*if(this.sort!=null) {
            	result=result.order_by(this.sort_group.concat(this.sort));
            }*/
			return result.filter(domain)
			.context(this.context)
			.lazy(false)
			.group_by(groupbys)
			.then(function (groups) {
			    return groups.filter(function (group) {
			        return group.attributes.length > 0;
			    }).map(function (group) {
			        var attrs = group.attributes,
			            grouped_on = attrs.grouped_on instanceof Array ? attrs.grouped_on : [attrs.grouped_on],
			            raw_grouped_on = grouped_on.map(function (f) {
			                return self.raw_field(f);
			            });
			        if (grouped_on.length === 1) {
			            attrs.value = [attrs.value];
			        }
			        attrs.value = _.range(grouped_on.length).map(function (i) {
			            var grp = grouped_on[i],
			                field = self.fields[grp];
			            if (attrs.value[i] === false) {
			                return _t('Undefined');
			            } else if (attrs.value[i] instanceof Array) {
			                return attrs.value[i][1];
			            } else if (field && field.type === 'selection') {
			                var selected = _.where(field.selection, {0: attrs.value[i]})[0];
			                return selected ? selected[1] : attrs.value[i];
			            }
			            return attrs.value[i];
			        });
			        attrs.aggregates.__count = group.attributes.length;
			        attrs.grouped_on = raw_grouped_on;
			        return group;
			    });
			});
        }
    });
}

