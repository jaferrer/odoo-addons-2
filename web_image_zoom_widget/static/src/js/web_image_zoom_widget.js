odoo.define('web_image_zoom_widget.image_zoom', function (require) {
    "use strict";

    var session = require('web.session');
    var utils = require('web.utils');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var _t = core._t;
    var QWeb = core.qweb;

    core.form_widget_registry.get("image").include({

        render_value: function () {
            this._super();
            var self = this;
            var url_img = this.placeholder;
            var src_img = this.options.src_img ? 'image' : this.name;
            var size_img = this.options.src_img ? 'large' : 'small';
            var $img = null;

            if (self.get('value')) {
                if (!utils.is_bin_size(self.get('value'))) {
                    url_img = 'data:image/png;base64,' + self.get('value');
                } else {
                    url_img = session.url('/web/image', {
                        model: self.view.dataset.model,
                        id: JSON.stringify(self.view.datarecord.id || null),
                        field: src_img,
                        unique: (self.view.datarecord.__last_update || '').replace(/[^0-9]/g, ''),
                    });
                }
            }
            $img = $(QWeb.render("FieldBinaryImage-img", {widget: self, url: url_img}));
            if (self.options.size) {
                $img.css("width", "" + self.options.size[0] + "px");
                $img.css("height", "" + self.options.size[1] + "px");
            }

            if (self.options.src_img) {
                self.$el.find('img.img.img-responsive').off().on('click', function () {
                    $img.css("width", "max-content");
                    $img.css("height", "max-content");
                    let modal = new Dialog(self, {
                        size: size_img,
                        dialogClass: 'o_act_window fgdgdsgf',
                        title: _t("Agrandissement"),
                        $content: $img,
                        buttons: [
                            {
                                text: _t("Close"), classes: 'btn-primary', close: true
                            }
                        ],
                    });
                    modal.open();
                    modal.$el.parent('.modal-content').css('max-height', 'none');
                });
            }
        },
    });
})

