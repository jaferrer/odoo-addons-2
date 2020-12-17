# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import traceback
import collections

from odoo.osv.expression import expression, create_substitution_leaf, normalize_domain, select_from_where, \
    select_distinct_from_where_not_null, _quote, ExtendedLeaf

OR_OPERATOR = '|'
AND_OPERATOR = '&'
FALSE_LEAF = (0, '=', 1)
FALSE_DOMAIN = [FALSE_LEAF]
TRUE_LEAF = (1, '=', 1)
NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

# _PARSE_ORIGINAL = expression.parse

_logger = logging.getLogger(__name__)


def parse_without_active_test(self):
    """ Transform the leaves of the expression

        The principle is to pop elements from a leaf stack one at a time.
        Each leaf is processed. The processing is a if/elif list of various
        cases that appear in the leafs (many2one, function fields, ...).
        Two things can happen as a processing result:
        - the leaf has been modified and/or new leafs have to be introduced
          in the expression; they are pushed into the leaf stack, to be
          processed right after
        - the leaf is added to the result

        Some internal var explanation:
            :var list path: left operand seen as a sequence of field names
                ("foo.bar" -> ["foo", "bar"])
            :var obj model: model object, model containing the field
                (the name provided in the left operand)
            :var obj field: the field corresponding to `path[0]`
            :var obj column: the column corresponding to `path[0]`
            :var obj comodel: relational model of field (field.comodel)
                (res_partner.bank_ids -> res.partner.bank)
    """
    cr, uid, context = self.root_model.env.args

    def to_ids(value, comodel):
        """ Normalize a single id or name, or a list of those, into a list of ids
            :param {int,long,basestring,list,tuple} value:
                if int, long -> return [value]
                if basestring, convert it into a list of basestrings, then
                if list of basestring ->
                    perform a name_search on comodel for each name
                    return the list of related ids
        """
        names = []
        if isinstance(value, basestring):
            names = [value]
        elif value and isinstance(value, (tuple, list)) and all(isinstance(item, basestring) for item in value):
            names = value
        elif isinstance(value, (int, long)):
            return [value]
        if names:
            return list({
                rid
                for name in names
                for rid, rname in comodel.name_search(name, [], 'ilike', limit=None)
            })
        return list(value)

    def child_of_domain(left, ids, left_model, parent=None, prefix=''):
        """ Return a domain implementing the child_of operator for [(left,child_of,ids)],
            either as a range using the parent_left/right tree lookup fields
            (when available), or as an expanded [(left,in,child_ids)] """
        if not ids:
            return FALSE_DOMAIN
        if left_model._parent_store and (not left_model.pool._init) and \
                (not context.get('defer_parent_store_computation')):
            # TODO: Improve where joins are implemented for many with '.', replace by:
            # doms += ['&',(prefix+'.parent_left','<',rec.parent_right),(prefix+'.parent_left','>=',rec.parent_left)]
            doms = []
            for rec in left_model.browse(ids):
                if doms:
                    doms.insert(0, OR_OPERATOR)
                doms += [AND_OPERATOR, ('parent_left', '<', rec.parent_right), ('parent_left', '>=', rec.parent_left)]
            if prefix:
                return [(left, 'in', left_model.with_context(active_test=False).search(doms).ids)]
            return doms
        else:
            parent_name = parent or left_model._parent_name
            child_ids = set(ids)
            while ids:
                ids = left_model.with_context(active_test=False).search([(parent_name, 'in', ids)]).ids
                child_ids.update(ids)
            return [(left, 'in', list(child_ids))]

    def parent_of_domain(left, ids, left_model, parent=None, prefix=''):
        """ Return a domain implementing the parent_of operator for [(left,parent_of,ids)],
            either as a range using the parent_left/right tree lookup fields
            (when available), or as an expanded [(left,in,parent_ids)] """
        if left_model._parent_store and (not left_model.pool._init) and \
                (not context.get('defer_parent_store_computation')):
            doms = []
            for rec in left_model.browse(ids):
                if doms:
                    doms.insert(0, OR_OPERATOR)
                doms += [AND_OPERATOR, ('parent_right', '>', rec.parent_left), ('parent_left', '<=', rec.parent_left)]
            if prefix:
                return [(left, 'in', left_model.search(doms).ids)]
            return doms
        else:
            parent_name = parent or left_model._parent_name
            parent_ids = set()
            for record in left_model.browse(ids):
                while record:
                    parent_ids.add(record.id)
                    record = record[parent_name]
            return [(left, 'in', list(parent_ids))]

    HIERARCHY_FUNCS = {'child_of': child_of_domain,
                       'parent_of': parent_of_domain}

    def pop():
        """ Pop a leaf to process. """
        return self.stack.pop()

    def push(leaf):
        """ Push a leaf to be processed right after. """
        self.stack.append(leaf)

    def push_result(leaf):
        """ Push a leaf to the results. This leaf has been fully processed
            and validated. """
        self.result.append(leaf)

    self.result = []
    self.stack = [ExtendedLeaf(leaf, self.root_model) for leaf in self.expression]
    # process from right to left; expression is from left to right
    self.stack.reverse()

    while self.stack:
        # Get the next leaf to process
        leaf = pop()

        # Get working variables
        if leaf.is_operator():
            left, operator, right = leaf.leaf, None, None
        elif leaf.is_true_leaf() or leaf.is_false_leaf():
            # because we consider left as a string
            left, operator, right = ('%s' % leaf.leaf[0], leaf.leaf[1], leaf.leaf[2])
        else:
            left, operator, right = leaf.leaf
        path = left.split('.', 1)

        model = leaf.model
        field = model._fields.get(path[0])
        comodel = model.env.get(getattr(field, 'comodel_name', None))

        # ----------------------------------------
        # SIMPLE CASE
        # 1. leaf is an operator
        # 2. leaf is a true/false leaf
        # -> add directly to result
        # ----------------------------------------

        if leaf.is_operator() or leaf.is_true_leaf() or leaf.is_false_leaf():
            push_result(leaf)

        # ----------------------------------------
        # FIELD NOT FOUND
        # -> from inherits'd fields -> work on the related model, and add
        #    a join condition
        # -> ('id', 'child_of', '..') -> use a 'to_ids'
        # -> but is one on the _log_access special fields, add directly to
        #    result
        #    TODO: make these fields explicitly available in self.columns instead!
        # -> else: crash
        # ----------------------------------------

        elif not field:
            raise ValueError("Invalid field %r in leaf %r" % (left, str(leaf)))

        elif field.inherited:
            # comments about inherits'd fields
            #  { 'field_name': ('parent_model', 'm2o_field_to_reach_parent',
            #                    field_column_obj, origina_parent_model), ... }
            parent_model = model.env[field.related_field.model_name]
            parent_fname = model._inherits[parent_model._name]
            leaf.add_join_context(parent_model, parent_fname, 'id', parent_fname)
            push(leaf)

        elif left == 'id' and operator in HIERARCHY_FUNCS:
            ids2 = to_ids(right, model)
            dom = HIERARCHY_FUNCS[operator](left, ids2, model)
            for dom_leaf in reversed(dom):
                new_leaf = create_substitution_leaf(leaf, dom_leaf, model)
                push(new_leaf)

        # ----------------------------------------
        # PATH SPOTTED
        # -> many2one or one2many with _auto_join:
        #    - add a join, then jump into linked column: column.remaining on
        #      src_table is replaced by remaining on dst_table, and set for re-evaluation
        #    - if a domain is defined on the column, add it into evaluation
        #      on the relational table
        # -> many2one, many2many, one2many: replace by an equivalent computed
        #    domain, given by recursively searching on the remaining of the path
        # -> note: hack about columns.property should not be necessary anymore
        #    as after transforming the column, it will go through this loop once again
        # ----------------------------------------

        elif len(path) > 1 and field.store and field.type == 'many2one' and field.auto_join:
            # res_partner.state_id = res_partner__state_id.id
            leaf.add_join_context(comodel, path[0], 'id', path[0])
            push(create_substitution_leaf(leaf, (path[1], operator, right), comodel))

        elif len(path) > 1 and field.store and field.type == 'one2many' and field.auto_join:
            # res_partner.id = res_partner__bank_ids.partner_id
            leaf.add_join_context(comodel, 'id', field.inverse_name, path[0])
            domain = field.domain(model) if callable(field.domain) else field.domain
            push(create_substitution_leaf(leaf, (path[1], operator, right), comodel))
            if domain:
                domain = normalize_domain(domain)
                for elem in reversed(domain):
                    push(create_substitution_leaf(leaf, elem, comodel))
                push(create_substitution_leaf(leaf, AND_OPERATOR, comodel))

        elif len(path) > 1 and field.store and field.auto_join:
            raise NotImplementedError('auto_join attribute not supported on field %s' % field)

        elif len(path) > 1 and field.store and field.type == 'many2one':
            right_ids = comodel.with_context(active_test=False).search([('.'.join(path[1:]), operator, right)]).ids
            leaf.leaf = (path[0], 'in', right_ids)
            push(leaf)

        # Making search easier when there is a left operand as one2many or many2many
        elif len(path) > 1 and field.store and field.type in ('many2many', 'one2many'):
            right_ids = comodel.search([('.'.join(path[1:]), operator, right)]).ids
            leaf.leaf = (path[0], 'in', right_ids)
            push(leaf)

        elif not field.store:
            # Non-stored field should provide an implementation of search.
            if not field.search:
                # field does not support search!
                _logger.error("Non-stored field %s cannot be searched.", field)
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug(''.join(traceback.format_stack()))
                # Ignore it: generate a dummy leaf.
                domain = []
            else:
                # Let the field generate a domain.
                if len(path) > 1:
                    right = comodel.search([('.'.join(path[1:]), operator, right)]).ids
                    operator = 'in'
                domain = field.determine_domain(model, operator, right)

            if not domain:
                leaf.leaf = TRUE_LEAF
                push(leaf)
            else:
                for elem in reversed(domain):
                    push(create_substitution_leaf(leaf, elem, model, internal=True))

        # -------------------------------------------------
        # RELATIONAL FIELDS
        # -------------------------------------------------

        # Applying recursivity on field(one2many)
        elif field.type == 'one2many' and operator in HIERARCHY_FUNCS:
            ids2 = to_ids(right, comodel)
            if field.comodel_name != model._name:
                dom = HIERARCHY_FUNCS[operator](left, ids2, comodel, prefix=field.comodel_name)
            else:
                dom = HIERARCHY_FUNCS[operator]('id', ids2, model, parent=left)
            for dom_leaf in reversed(dom):
                push(create_substitution_leaf(leaf, dom_leaf, model))

        elif field.type == 'one2many':
            call_null = True

            domain = field.domain
            if callable(domain):
                domain = domain(model)
            is_integer_m2o = comodel._fields[field.inverse_name].type == 'integer'
            if right is not False:
                if isinstance(right, basestring):
                    op = {'!=': '=', 'not like': 'like', 'not ilike': 'ilike'}.get(operator, operator)
                    ids2 = [x[0] for x in comodel.name_search(right, domain or [], op, limit=None)]
                    if ids2:
                        operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                else:
                    if isinstance(right, collections.Iterable):
                        ids2 = right
                    else:
                        ids2 = [right]
                    if ids2 and is_integer_m2o and domain:
                        ids2 = comodel.search([('id', 'in', ids2)] + domain).ids

                if not ids2:
                    if operator in ['like', 'ilike', 'in', '=']:
                        # no result found with given search criteria
                        call_null = False
                        push(create_substitution_leaf(leaf, FALSE_LEAF, model))
                else:
                    # determine ids1 <-- field.inverse_name --- ids2
                    if comodel._fields[field.inverse_name].store:
                        ids1 = select_from_where(cr, field.inverse_name, comodel._table, 'id', ids2, operator)
                    else:
                        recs = comodel.browse(ids2).sudo().with_context(prefetch_fields=False)
                        ids1 = recs.mapped(field.inverse_name)
                        if not is_integer_m2o:
                            ids1 = ids1.ids
                    if ids1:
                        call_null = False
                        o2m_op = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                        push(create_substitution_leaf(leaf, ('id', o2m_op, ids1), model))
                    elif operator in ('like', 'ilike', 'in', '='):
                        # no match found with positive search operator => no result (FALSE_LEAF)
                        call_null = False
                        push(create_substitution_leaf(leaf, FALSE_LEAF, model))

            if call_null:
                o2m_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                # determine ids from field.inverse_name
                if comodel._fields[field.inverse_name].store and not (is_integer_m2o and domain):
                    ids1 = select_distinct_from_where_not_null(cr, field.inverse_name, comodel._table)
                else:
                    comodel_domain = [(field.inverse_name, '!=', False)]
                    if is_integer_m2o and domain:
                        comodel_domain += domain
                    recs = comodel.search(comodel_domain).sudo().with_context(prefetch_fields=False)
                    ids1 = recs.mapped(field.inverse_name)
                    if not is_integer_m2o:
                        ids1 = ids1.ids
                push(create_substitution_leaf(leaf, ('id', o2m_op, ids1), model))

        elif field.type == 'many2many':
            rel_table, rel_id1, rel_id2 = field.relation, field.column1, field.column2

            if operator in HIERARCHY_FUNCS:
                ids2 = to_ids(right, comodel)
                dom = HIERARCHY_FUNCS[operator]('id', ids2, comodel)
                ids2 = comodel.search(dom).ids
                if comodel == model:
                    push(create_substitution_leaf(leaf, ('id', 'in', ids2), model))
                else:
                    subquery = 'SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % (rel_id1, rel_table, rel_id2)
                    # avoid flattening of argument in to_sql()
                    subquery = cr.mogrify(subquery, [tuple(ids2)])
                    push(create_substitution_leaf(leaf, ('id', 'inselect', (subquery, [])), internal=True))
            else:
                call_null_m2m = True
                if right is not False:
                    if isinstance(right, basestring):
                        op = {'!=': '=', 'not like': 'like', 'not ilike': 'ilike'}.get(operator, operator)
                        domain = field.domain
                        if callable(domain):
                            domain = domain(model)
                        res_ids = [x[0] for x in comodel.name_search(right, domain or [], op, limit=None)]
                        if res_ids:
                            operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                    else:
                        if not isinstance(right, list):
                            res_ids = [right]
                        else:
                            res_ids = right
                    if not res_ids:
                        if operator in ['like', 'ilike', 'in', '=']:
                            # no result found with given search criteria
                            call_null_m2m = False
                            push(create_substitution_leaf(leaf, FALSE_LEAF, model))
                        else:
                            operator = 'in'  # operator changed because ids are directly related to main object
                    else:
                        call_null_m2m = False
                        subop = 'not inselect' if operator in NEGATIVE_TERM_OPERATORS else 'inselect'
                        subquery = 'SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % (rel_id1, rel_table, rel_id2)
                        # avoid flattening of argument in to_sql()
                        subquery = cr.mogrify(subquery, [tuple(filter(None, res_ids))])
                        push(create_substitution_leaf(leaf, ('id', subop, (subquery, [])), internal=True))

                if call_null_m2m:
                    m2m_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                    push(create_substitution_leaf(
                        leaf,
                        ('id', m2m_op, select_distinct_from_where_not_null(cr, rel_id1, rel_table)), model))

        elif field.type == 'many2one':
            if operator in HIERARCHY_FUNCS:
                ids2 = to_ids(right, comodel)
                if field.comodel_name != model._name:
                    dom = HIERARCHY_FUNCS[operator](left, ids2, comodel, prefix=field.comodel_name)
                else:
                    dom = HIERARCHY_FUNCS[operator]('id', ids2, model, parent=left)
                for dom_leaf in reversed(dom):
                    push(create_substitution_leaf(leaf, dom_leaf, model))
            else:
                def _get_expression(comodel, left, right, operator):
                    # Special treatment to ill-formed domains
                    operator = (operator in ['<', '>', '<=', '>=']) and 'in' or operator

                    dict_op = {'not in': '!=', 'in': '=', '=': 'in', '!=': 'not in'}
                    if isinstance(right, tuple):
                        right = list(right)
                    if (not isinstance(right, list)) and operator in ['not in', 'in']:
                        operator = dict_op[operator]
                    elif isinstance(right, list) and operator in ['!=',
                                                                  '=']:  # for domain (FIELD,'=',['value1','value2'])
                        operator = dict_op[operator]
                    res_ids = [x[0] for x in
                               comodel.with_context(active_test=False).name_search(right, [], operator, limit=None)]
                    if operator in NEGATIVE_TERM_OPERATORS:
                        res_ids.append(False)  # TODO this should not be appended if False was in 'right'
                    return left, 'in', res_ids

                # resolve string-based m2o criterion into IDs
                if isinstance(right, basestring) or \
                        right and isinstance(right, (tuple, list)) and all(
                        isinstance(item, basestring) for item in right):
                    push(create_substitution_leaf(leaf, _get_expression(comodel, left, right, operator), model))
                else:
                    # right == [] or right == False and all other cases are handled by __leaf_to_sql()
                    push_result(leaf)

        # -------------------------------------------------
        # BINARY FIELDS STORED IN ATTACHMENT
        # -> check for null only
        # -------------------------------------------------

        elif field.type == 'binary' and field.attachment:
            if operator in ('=', '!=') and not right:
                inselect_operator = 'inselect' if operator in NEGATIVE_TERM_OPERATORS else 'not inselect'
                subselect = "SELECT res_id FROM ir_attachment WHERE res_model=%s AND res_field=%s"
                params = (model._name, left)
                push(create_substitution_leaf(leaf, ('id', inselect_operator, (subselect, params)), model,
                                              internal=True))
            else:
                _logger.error("Binary field '%s' stored in attachment: ignore %s %s %s",
                              field.string, left, operator, right)
                leaf.leaf = TRUE_LEAF
                push(leaf)

        # -------------------------------------------------
        # OTHER FIELDS
        # -> datetime fields: manage time part of the datetime
        #    column when it is not there
        # -> manage translatable fields
        # -------------------------------------------------

        else:
            if field.type == 'datetime' and right and len(right) == 10:
                if operator in ('>', '<='):
                    right += ' 23:59:59'
                else:
                    right += ' 00:00:00'
                push(create_substitution_leaf(leaf, (left, operator, right), model))

            elif field.translate is True and right:
                need_wildcard = operator in ('like', 'ilike', 'not like', 'not ilike')
                sql_operator = {'=like': 'like', '=ilike': 'ilike'}.get(operator, operator)
                if need_wildcard:
                    right = '%%%s%%' % right

                inselect_operator = 'inselect'
                if sql_operator in NEGATIVE_TERM_OPERATORS:
                    # negate operator (fix lp:1071710)
                    sql_operator = sql_operator[4:] if sql_operator[:3] == 'not' else '='
                    inselect_operator = 'not inselect'

                unaccent = self._unaccent if sql_operator.endswith('like') else lambda x: x

                instr = unaccent('%s')

                if sql_operator == 'in':
                    # params will be flatten by to_sql() => expand the placeholders
                    instr = '(%s)' % ', '.join(['%s'] * len(right))

                subselect = """WITH temp_irt_current (id, name) as (
                        SELECT ct.id, coalesce(it.value,ct.{quote_left})
                        FROM {current_table} ct
                        LEFT JOIN ir_translation it ON (it.name = %s and
                                    it.lang = %s and
                                    it.type = %s and
                                    it.res_id = ct.id and
                                    it.value != '')
                        )
                        SELECT id FROM temp_irt_current WHERE {name} {operator} {right} order by name
                        """.format(current_table=model._table, quote_left=_quote(left), name=unaccent('name'),
                                   operator=sql_operator, right=instr)

                params = (
                    model._name + ',' + left,
                    model.env.lang or 'en_US',
                    'model',
                    right,
                )
                push(create_substitution_leaf(leaf, ('id', inselect_operator, (subselect, params)), model,
                                              internal=True))

            else:
                push_result(leaf)

    # ----------------------------------------
    # END OF PARSING FULL DOMAIN
    # -> generate joins
    # ----------------------------------------

    joins = set()
    for leaf in self.result:
        joins |= set(leaf.get_join_conditions())
    self.joins = list(joins)


expression.parse = parse_without_active_test
