odoo.define("pos_change_logo.image", function (require) {
    "use strict";
    var PosBaseWidget = require('point_of_sale.chrome');
    var models = require("point_of_sale.models");

    var exports = {};

    var _pictures = _.findWhere(
        models.PosModel.prototype.models,
        {label: "pictures"}
    );

    PosBaseWidget.Chrome.include({
        renderElement: function () {

            var self = this;

            if (self.pos.config) {
                if (self.pos.config.image) {
                    this.flag = 1
                    this.a3 = window.location.origin + '/web/image?model=pos.config&field=image&id=' + self.pos.config.id;
                }
            }
            this._super(this);
        }
    });

    _pictures.loaded = function (self) {
        self.company_logo = new Image();
        var logo_loaded = new $.Deferred();
        self.company_logo.onload = function () {
            var img = self.company_logo;
            var ratio = 1;
            var targetwidth = 260;
            var maxheight = 120;
            if (img.width !== targetwidth) {
                ratio = targetwidth / img.width;
            }
            if (img.height * ratio > maxheight) {
                ratio = maxheight / img.height;
            }
            var width = Math.floor(img.width * ratio);
            var height = Math.floor(img.height * ratio);
            var c = document.createElement('canvas');
            c.width = width;
            c.height = height;
            var ctx = c.getContext('2d');
            ctx.drawImage(self.company_logo, 0, 0, width, height);
            self.company_logo_base64 = c.toDataURL();
            logo_loaded.resolve();
        };
        self.company_logo.onerror = function () {
            logo_loaded.reject();
        };
        self.company_logo.crossOrigin = "anonymous";
        self.company_logo.src = window.location.origin + '/web/image?model=pos.config&field=image&id=' + self.config.id;
        return logo_loaded;
    };

    return exports;

});