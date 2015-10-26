import os
from os import listdir
from os.path import isfile, join
from openerp import models, api, tools
from openerp.tools.config import config

class loadCss(models.TransientModel):
    _name = 'load.css'

    @api.model
    def load_list_css(self):
        ad = os.path.abspath(os.path.join(tools.ustr(config['root_path']), u'addons'))
        mod_path_list = map(lambda m: os.path.abspath(tools.ustr(m.strip())), config['addons_path'].split(','))
        mod_path_list.append(ad)
        mod_path_list = list(set(mod_path_list))
        pathmod = "portail_ndp/static/src/css"
        for mod_path in mod_path_list:
            if os.path.lexists(mod_path+os.path.sep+pathmod):
                filepath = mod_path+os.path.sep+pathmod
                break
        
        onlyfiles=[]
        if filepath :
            onlyfiles = [ f for f in listdir(filepath) if isfile(join(filepath,f)) ]
        
        return onlyfiles