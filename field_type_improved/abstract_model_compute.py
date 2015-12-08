from openerp import models, fields, api
import psycopg2
import logging
from openerp import SUPERUSER_ID

logger = logging.getLogger(__name__)


class AbstractModelCompute(models.AbstractModel):
    _name = "abstract.model.compute.field"

    fields.Field._slots["compute_sql"] = False

    _sql_computed_field_sql = {}
    """
        example :
        fields.Boolean('name',compute_sql=True)
        self._sql_computed_field_sql[key]=script_sql
        
        use to  inherit = []
    """

    def init(self, cr):
        if hasattr(super(AbstractModelCompute, self), 'init'):
            super(self, AbstractModelCompute).init()

        if self._name == "abstract.model.compute.field":
            return

        self.create_or_update_if_needs_compute_Field_sql(cr, SUPERUSER_ID)

    def create_or_update_if_needs_compute_Field_sql(self, cr, uid, context=None):
        def_drop = "drop function if exists %s(pricelist_partnerinfo);"
        def_create_header = """ create function %s (pricelist_partnerinfo) returns %s as $func$
        
        """
        def_create_footer = """
$func$ LANGUAGE sql stable;
        """

        for i in self._sql_computed_field_sql:
            print i
            # print self[i]
            # print self[i]._attrs['compute_sql']
#            if self[i] and self[i]._attrs['compute_sql'] and self._sql_computed_field_sql[i]:
            script_sql = def_drop % i
            print script_sql
            cr.execute(script_sql)
            cr.execute("alter table pricelist_partnerinfo drop column if exists %s;" % i)
            script_sql = (
                def_create_header + self._sql_computed_field_sql[i] + def_create_footer) % (i, 'boolean')
            print script_sql
            cr.execute(script_sql)
