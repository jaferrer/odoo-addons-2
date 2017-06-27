# Feature :

## Improved on change feature
##### Possibity to return a custom action to triggers in the on_change method
##### add 2 decorator
###### @api.onchange_action('field_name')
Return a decorator to decorate an onchange action method for given fields.

Each argument must be a field name

```
@api.onchange_action('partner_id')
def _onchange_partner_action(self):
    return <your action def here>
```

The method may return action dict
```
ctx = dict(self.env.context)
return {
'name': _('My Wizard name'),
'view_type': 'form',
'view_mode': 'form',
'res_model': 'my.model.wizard',
'domain': [],
'context': ctx,
'views': [[False, 'form']],
'type': 'ir.actions.act_window',
'target': 'new'
}
```
The method may return action ID

``return self.['ir.ui.act_window'].search((['your', 'domain', 'here'])).id``

or The method may return action xmlID

``return self.['ir.model.data'].search((['your', 'domain', 'here'])).name``
.. warning::

``@onchange_action`` only supports simple field names, dotted names
(fields of relational fields e.g. ``partner_id.tz``) are not
supported and will be ignored

###### @api.onchange_action_id
Return a decorator to decorate an onchange action method for given fields.
The argument can be an xml id
```
@api.onchange('partner_id')
@api.onchange_action_id('my_module.my_xml_id')
def _onchange_partner(self):
    self.message = "Dear %s" % (self.partner_id.name or "")
```

Or the argument can be a hard coded Database action id
```
@api.onchange('partner_id')
@api.onchange_action_id(123)
def _onchange_partner(self):
    self.message = "Dear %s" % (self.partner_id.name or "")
```
###### The model 'on_change.action'
It's a abstract model that offer all the facility see above
```
class MyNewModel(models.Models):
    _name = 'my.model'
    _inherit = 'on_change.action'

```
You can define a new method called `_action_on_change_action_on_change(self, field_name, field_values)`
 This method return a dict.
 The dict can take 2 defferente strucure
```
 mdict =  {
 'field_name_1' : {<my action dict>},
 'field_name_2' : {<my action dict>}
 }
 ```
 Or only ```mdict = <my action dict>```

 If you want you can return directly an xml ID or a DB id
 instead of the `<my action dict>`
