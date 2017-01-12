openerp.web_listview_groupby_page = function(instance) {
	
	var _lt = openerp.web._lt;
	var _t = openerp.web._t;

	var QWeb = instance.web.qweb;
	
	instance.web.Query.include({
		
		_execute: function (options) {
	        var self = this;
	        options = options || {};
	        return instance.session.rpc('/web/dataset/search_read', {
	            model: this._model.name,
	            fields: this._fields || false,
	            domain: instance.web.pyeval.eval('domains',
	                    [this._model.domain(this._filter)]),
	            context: instance.web.pyeval.eval('contexts',
	                    [this._model.context(this._context)]),
	            offset: this._offset,
	            limit: this._limit,
	            sort: instance.web.serialize_sort(this._order_by)
	        }, options).then(function (results) {
	            self._count = results.length;
	            return results.records;
	        }, null);
	    },
	    
		group_by: function (grouping) {
	        var ctx = instance.web.pyeval.eval(
	            'context', this._model.context(this._context));

	        // undefined passed in explicitly (!)
	        if (_.isUndefined(grouping)) {
	            grouping = [];
	        }

	        if (!(grouping instanceof Array)) {
	            grouping = _.toArray(arguments);
	        }
	        if (_.isEmpty(grouping) && !ctx['group_by_no_leaf']) {
	            return null;
	        }
	        var raw_fields = _.map(grouping.concat(this._fields || []), function (field) {
	            return field.split(':')[0];
	        });

	        var self = this;
	        return this._model.call('read_group', {
	            groupby: grouping,
	            fields: _.uniq(raw_fields),
	            domain: this._model.domain(this._filter),
	            context: ctx,
	            offset: this._offset,
	            lazy: this._lazy,
	            limit: this._limit,
	            orderby: instance.web.serialize_sort(this._order_by) || false
	        }).then(function (results) {
	            return _(results).map(function (result) {
	                // FIX: querygroup initialization
	                result.__context = result.__context || {};
	                result.__context.group_by = result.__context.group_by || [];
	                _.defaults(result.__context, ctx);
	                var grouping_fields = self._lazy ? [grouping[0]] : grouping;
	                return new instance.web.QueryGroup(
	                    self._model.name, grouping_fields, result);
	            });
	        });
	    }
	});
	
	instance.web.ListView.include({
		init: function(parent, dataset, view_id, options) {
			this._super(parent, dataset, view_id, options);
			if (this.dataset instanceof instance.web.DataSetStatic) {
	            this.groups.datagroup = new StaticDataGroup(this.dataset);
	        } else {
	            this.groups.datagroup = new DataGroup(
	                this, this.model,
	                dataset.get_domain(),
	                dataset.get_context());
	            this.groups.datagroup.sort = this.dataset._sort;
	            this._limitgroup=this.limit();
	            this.groups.datagroup.limit = this._limitgroup;
	            this.groups.datagroup.page=0;
	            this.pagegroup=0;
	        }
		},
		do_search: function (domain, context, group_by) {
	        this.groups.datagroup = new DataGroup(
	            this, this.model, domain, context, group_by);
	        this.groups.datagroup.sort = this.dataset._sort;
	        this.groups.datagroup.limit=this._limitgroup;
	        this.groups.datagroup.page=this.pagegroup;
	        if (_.isEmpty(group_by) && !context['group_by_no_leaf']) {
	            group_by = null;
	        }
	        this.no_leaf = !!context['group_by_no_leaf'];
	        this.grouped = !!group_by;

	        return this.alive(this.load_view(context)).then(
	            this.proxy('reload_content'));
	    },
	    load_list: function(data) {
	    	this._super(data);
	        // Pager
	    	var self=this;
	        if (!this.$pagergroup) {
	            this.$pagergroup = $(QWeb.render("ListView.pagergroup", {'widget':self}));
	            if (this.options.$buttons) {
	                this.$pagergroup.appendTo(this.options.$pager);
	            } else {
	                this.$el.find('.oe_list_pager_group').replaceWith(this.$pagergroup);
	            }

	            this.$pagergroup
	                .on('click', 'a[data-pager-action]', function () {
	                    var $this = $(this);
	                    var max_pagegroup_index = Math.ceil(self.dataset.size() / self._limitgroup) - 1;
	                    switch ($this.data('pager-action')) {
	                        case 'first':
	                            self.pagegroup = 0;
	                            break;
	                        case 'last':
	                            self.pagegroup = max_pagegroup_index;
	                            break;
	                        case 'next':
	                            self.pagegroup += 1;
	                            break;
	                        case 'previous':
	                            self.pagegroup -= 1;
	                            break;
	                    }
	                    if (self.pagegroup < 0) {
	                        self.pagegroup = max_pagegroup_index;
	                    } else if (self.pagegroup > max_pagegroup_index) {
	                        self.pagegroup = 0;
	                    }
	                    self.groups.datagroup.page=self.pagegroup;
	                    self.reload_content();
	                }).find('.oe_list_pager_state')
	                    .click(function (e) {
	                        e.stopPropagation();
	                        var $this = $(this);

	                        var $select = $('<select>')
	                            .appendTo($this.empty())
	                            .click(function (e) {e.stopPropagation();})
	                            .append('<option value="80">80</option>' +
	                                    '<option value="200">200</option>' +
	                                    '<option value="500">500</option>' +
	                                    '<option value="2000">2000</option>' +
	                                    '<option value="NaN">' + _t("Unlimited") + '</option>')
	                            .change(function () {
	                                var val = parseInt($select.val(), 10);
	                                self._limitgroup = (isNaN(val) ? null : val);
	                                
	                                self.pagegroup = 0;
	                                self.groups.datagroup.limit=self._limitgroup;
	                                self.groups.datagroup.page=self.pagegroup;
	                                self.reload_content();
	                            }).blur(function() {
	                                $(this).trigger('change');
	                            })
	                            .val(self._limit || 'NaN');
	                    });
	            	
	        }
	        this.$pagergroup.hide();
	    },
	    do_show: function () {
	        this._super();
	        if (this.$pagergroup) {
	            this.$pagergroup.show();
	        }
	    },
	    do_hide: function () {
	        if (this.$pagergroup) {
	            this.$pagergroup.hide();
	        }
	        this._super();
	    },
	    
	    configure_pager: function (dataset) {
	    	if(!Array.isArray(dataset)) {
	    		this.$pagergroup.hide();
	    		this.pagegroup=0;
	    		this._super(dataset);
	    	} else {
		    	this.$pagergroup.hide();
		    	this.dataset.ids = dataset.ids;
	
		        var limit = this._limitgroup;
		        var spager = '-';
	            var range_start = this.pagegroup * limit + 1;
	            var range_stop = range_start - 1 + limit;
	            if (this.records.length) {
	                range_stop = range_start - 1 + this.records.length;
	            }
	            spager = _.str.sprintf(_t("%d-%d"), range_start, range_stop);
	            if(dataset.length>0 && dataset.length==limit) {
	            	this.$pagergroup.show();
	            }
	            if(this.pagegroup>0) {
	            	this.$pagergroup.find(".oe_i").first().show();
	            	if(dataset.length==0 || dataset.length<limit) {
	            		this.$pagergroup.show();
	            		this.$pagergroup.find(".oe_i").last().hide();
	            	}
	            }
	            if(this.pagegroup==0) {
	            	this.$pagergroup.find(".oe_i").last().show();
	            	this.$pagergroup.find(".oe_i").first().hide();
	            }
	            
		        this.$pagergroup.find('.oe_list_pager_state').text(spager);
	    	}
	    },
	    
	    
	});
	
	instance.web.ListView.Groups.include({
		render: function (post_render) {
	        var self = this;
	        var $el = $('<tbody>');
	        this.elements = [$el[0]];

	        this.datagroup.list(
	            _(this.view.visible_columns).chain()
	                .filter(function (column) { return column.tag === 'field';})
	                .pluck('name').value(),
	            function (groups) {
	                // page count is irrelevant on grouped page, replace by limit
	            	self.view.configure_pager(groups);
	                self.view.$pager.hide();
	                //self.view.$pager.find('.oe_list_pager_state').text(self.view._limit ? self.view._limit : '∞');
	                $el[0].appendChild(
	                    self.render_groups(groups));
	                if (post_render) { post_render(); }
	            }, function (dataset) {
	                self.render_dataset(dataset).then(function (list) {
	                    self.children[null] = list;
	                    self.elements =
	                        [list.$current.replaceAll($el)[0]];
	                    self.setup_resequence_rows(list, dataset);
	                }).always(function() {
	                    if (post_render) { post_render(); }
	                });
	            });
	        return $el;
	    }
	    
	});

	instance.web.FormView.include({
		do_update_pager: function(hide_index) {
			if (this.dataset.ids == undefined){
				this.dataset.ids = [];
			}
        this.$pager.toggle(this.dataset.ids.length > 1);
        if (hide_index) {
            $(".oe_form_pager_state", this.$pager).html("");
        } else {
            $(".oe_form_pager_state", this.$pager).html(_.str.sprintf(_t("%d / %d"), this.dataset.index + 1, this.dataset.ids.length));
        }
    },
	});
	
	var DataGroup =  instance.web.Class.extend({
		   init: function(parent, model, domain, context, group_by, level) {
		       this.model = new instance.web.Model(model, context, domain);
		       this.group_by = group_by;
		       this.context = context;
		       this.domain = domain;

		       this.level = level || 0;
		   },
		   list: function (fields, ifGroups, ifRecords) {
		       var self = this;
		       if (!_.isEmpty(this.group_by)) {
		           // ensure group_by fields are read.
		           fields = _.unique((fields || []).concat(this.group_by));
		       }

		       var query = this.model.query(fields).order_by(this.sort).limit((this.limit!=undefined)?this.limit:false).offset((this.limit!=undefined)?this.page*this.limit:0).group_by(this.group_by);
		       $.when(query).done(function (querygroups) {
		           // leaf node
		           if (!querygroups) {
		               var ds = new instance.web.DataSetSearch(self, self.model.name, self.model.context(), self.model.domain());
		               ds._sort = self.sort;
		               ifRecords(ds);
		               return;
		           }
		           // internal node
		           var child_datagroups = _(querygroups).map(function (group) {
		               var child_context = _.extend(
		                   {}, self.model.context(), group.model.context());
		               var child_dg = new DataGroup(
		                   self, self.model.name, group.model.domain(),
		                   child_context, group.model._context.group_by,
		                   self.level + 1);
		               child_dg.sort = self.sort;
		               // copy querygroup properties
		               child_dg.__context = child_context;
		               child_dg.__domain = group.model.domain();
		               child_dg.folded = group.get('folded');
		               child_dg.grouped_on = group.get('grouped_on');
		               child_dg.length = group.get('length');
		               child_dg.value = group.get('value');
		               child_dg.openable = group.get('has_children');
		               child_dg.aggregates = group.get('aggregates');
		               return child_dg;
		           });
		           ifGroups(child_datagroups);
		       });
		   }
		});
	
	var StaticDataGroup = DataGroup.extend({
		   init: function (dataset) {
		       this.dataset = dataset;
		   },
		   list: function (fields, ifGroups, ifRecords) {
		       ifRecords(this.dataset);
		   }
		});
}

