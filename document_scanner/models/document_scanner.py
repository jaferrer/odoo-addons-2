import tempfile
import sys
import os.path
import time
import base64
from openerp import fields, models, api, tools
from openerp.tools.config import config

try :
    import sane
except :
    pass

class DocumentScannerUser(models.Model):
    _inherit = "res.users"
    
    def _get_devices_options(self):
        devices=eval(self.env['ir.config_parameter'].get_param('sirail.list_scanner', default='[]'))
        print('Available devices:', devices)
        res=[]
        for item in devices:
            res.append((item[0],"%s - %s"%(item[1],item[2])))
        return res
    
    scanner=fields.Selection(selection=_get_devices_options,string='Scanner')
    
    @api.model
    def update_list_scanner(self):
        sane.init()
        self.env['ir.config_parameter'].set_param('sirail.list_scanner', str(sane.get_devices(False)))
        print(self.env['ir.config_parameter'].get_param('sirail.list_scanner', default='[]'))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class IrAttachmentScanner(models.Model):
    _inherit = "ir.attachment"
    
    
    @api.model
    def scan(self,ctx):
        self.env.context = ctx
        ad = os.path.abspath(os.path.join(tools.ustr(config['root_path']), u'addons'))
        mod_path_list = map(lambda m: os.path.abspath(tools.ustr(m.strip())), config['addons_path'].split(','))
        mod_path_list.append(ad)
        mod_path_list = list(set(mod_path_list))
        pathmod = "document_scanner/shell/scantopdf.sh"
        outputfile = "scan_%s_%s.pdf"%(self.env.user.id,time.strftime("%H%M%S"))
        path=tempfile.tempdir
        device=self.env.user.scanner
        status=0
        for mod_path in mod_path_list:
            if os.path.lexists(mod_path+os.path.sep+pathmod.split(os.path.sep)[0]):
                filepath = mod_path+os.path.sep+pathmod
                status = os.system('sh %s %s %s %s %s'%(filepath, outputfile, path, device, self.env.user.id))
                break
        
        
        if os.path.lexists(path+os.path.sep+outputfile) :
            ufile= open(path+os.path.sep+outputfile,"r")
            self.env['ir.attachment'].create({
                'name': outputfile,
                'datas': base64.encodestring(ufile.read()),
                'datas_fname': outputfile,
                'res_model': self.env.context['active_model'],
                'res_id': int(self.env.context['active_id'])
            })
            ufile.close()
            os.remove(path+os.path.sep+outputfile)
            return {
                        "file":outputfile
                    }
        else :
            return {
                        "error":status
                    }

