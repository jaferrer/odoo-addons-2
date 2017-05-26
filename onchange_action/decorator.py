from openerp import api


def onchange_action(*args):
    """ Return a decorator to decorate an onchange action method for given fields.
        Each argument must be a field name::
            @api.onchange('partner_id')
            def _onchange_partner(self):
                self.message = "Dear %s" % (self.partner_id.name or "")

        In the form views where the field appears, the method will be called
        when one of the given fields is modified. The method is invoked on a
        pseudo-record that contains the values present in the form. Field
        assignments on that record are automatically sent back to the client.

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

            ``@onchange`` only supports simple field names, dotted names
            (fields of relational fields e.g. ``partner_id.tz``) are not
            supported and will be ignored
    """
    return lambda method: api.decorate(method, '_onchange_action', args)


def onchange_action_id(args):
    """ Return a decorator to decorate an onchange action method for given fields.
        The argument can be an xml id::
            @api.onchange('partner_id')
            @api.onchange_action_id('my_module.my_xlm_id')
            def _onchange_partner(self):
                self.message = "Dear %s" % (self.partner_id.name or "")
        Or the argument can be a hard coded Database action id
            @api.onchange('partner_id')
            @api.onchange_action_id(123)
            def _onchange_partner(self):
                self.message = "Dear %s" % (self.partner_id.name or "")
    """
    return lambda method: api.decorate(method, '_onchange_action_id', args)


api.onchange_action = onchange_action
api.onchange_action_id = onchange_action_id
