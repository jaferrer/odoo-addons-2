### Exemples

Le module ajoute un example sur les res.partner

Exemple d'utilisation pour les hr.employee

```
<record id="view_organization_chart_employee" model="ir.ui.view">
    <field name="model">hr.employee</field>
    <field name="type">organization_chart</field>
    <field name="field_parent">parent_id</field>
    <field name="arch" type="xml">
        <organization_chart>
            <field name="parent_id"/>
            <field name="work_email"/>
            <field name="gender"/>
            <templates>
                <div t-name="chart-item">
                    <span t-esc="record.work_email"/><br/>
                    <span t-esc="record.gender"/>
                </div>
            </templates>
        </organization_chart>
    </field>
</record>

<record id="hr.open_view_employee_list_my" model="ir.actions.act_window">
    <field name="view_mode">tree,form,kanban,organization_chart</field>
</record>
```