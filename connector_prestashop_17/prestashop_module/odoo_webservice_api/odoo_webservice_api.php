<?php

if (!defined('_PS_VERSION_')) {
    exit;
}

class Odoo_Webservice_API extends Module
{

    public function __construct()
    {
        $this->name = 'odoo_webservice_api';
        $this->tab = 'administration';
        $this->version = '0';
        $this->author = 'NDP Systèmes';
        $this->need_instance = 0;
        $this->ps_versions_compliancy = array('min' => '1.7', 'max' => '1.7.7');
        $this->bootstrap = true;

        parent::__construct();

        $this->displayName = 'Compléments WS pour Odoo';
    }

    public function install()
    {
	    if (!parent::install() || !$this->registerHook('addWebserviceResources')) return false;
	    return true;
    }

    public function hookAddWebserviceResources($params) {
        return array(
            'order_cart_rules' => array(
                'description' => 'The Order cart rules',
                'class' => 'OrderCartRule'
            ),
        );
    }
}
?>