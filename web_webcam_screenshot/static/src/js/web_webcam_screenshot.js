odoo.define('web_webcam_screenshot.webcam_screenshot_widget', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var Sidebar = require('web.Sidebar');
    var Model = require('web.DataModel');
    var data = require('web.data');

    var _t = core._t;
    var QWeb = core.qweb;
    var videostream;

    core.form_widget_registry.get("image").include({
        render_value: function () {
            this._super();

            var self = this,
                WebCamDialog = $(QWeb.render("WebCamScreenShotDialog")),
                canvas,
                video,
                img;

            self.$el.find('.o_form_binary_file_webcam_screenshot').removeClass('col-md-offset-5');
            self.$el.find('.o_form_binary_file_webcam_screenshot').off().on('click', function () {
                // Init Webcam
                new Dialog(self, {
                    size: 'large',
                    dialogClass: 'o_act_window',
                    title: _t("WebCam screenshot"),
                    $content: WebCamDialog,
                    buttons: [
                        {
                            text: _t("Launch webcam"), classes: 'btn btn-primary capture-button',
                            click: function () {
                                navigator.mediaDevices.getUserMedia({
                                    video: {width: {max: 320}, height: {max: 240}}
                                }).then(function (stream) {
                                    videostream = stream;
                                    video = document.querySelector('#screenshot video');
                                    video.srcObject = videostream;
                                    canvas = document.createElement('canvas');
                                    img = document.querySelector('#screenshot-img');
                                }).catch(function (error) {
                                    alert("Error with webcam : " + error);
                                });
                            }
                        },
                        {
                            text: _t("Take screenshot"), classes: 'btn btn-primary screenshot-button',
                            click:
                                function () {
                                    canvas.width = video.videoWidth;
                                    canvas.height = video.videoHeight;
                                    canvas.getContext('2d').drawImage(video, 0, 0);
                                    // Other browsers will fall back to image/png
                                    img.src = canvas.toDataURL('image/png');
                                    $('.save_close_btn').removeAttr('disabled');
                                    videostream.getTracks()[0].stop();
                                }
                        },
                        {
                            text: _t("Save & Close"), classes: 'btn-primary save_close_btn', close: true,
                            click:
                                function () {
                                    var img_data_base64 = img.src.split(',')[1];
                                    // From the above info, we doing the opposite stuff to find the approx size of Image in bytes.
                                    var approx_img_size = 3 * (img_data_base64.length / 4); // like... "3[n/4]"
                                    // Upload image in Binary Field
                                    self.on_file_uploaded(approx_img_size, "web-cam-preview.jpeg", "image/jpeg", img_data_base64);
                                }
                        },
                        {
                            text: _t("Close"), close: true
                        }
                    ]
                }).open();
                // At time of Init "Save & Close" button is disabled
                // Placeholder Image in the div "webcam_result"
                $('.save_close_btn').attr('disabled', 'disabled');
                WebCamDialog.find("#screenshot-img").attr({'src': "/web_widget_image_webcam/static/src/img/webcam_placeholder.png"});
            });
        },
    });

    Sidebar.include({
        start: function () {
            this._super();
            var sidebar_instance = this;
            this.$el.on('click', '.oe_sidebar_webcam_screenshot', function (event) {
                var self = this,
                    WebCamDialog = $(QWeb.render("WebCamScreenShotDialog")),
                    canvas,
                    video,
                    img;

                new Dialog(self, {
                    size: 'large',
                    dialogClass: 'o_act_window',
                    title: _t("WebCam screenshot"),
                    $content: WebCamDialog,
                    buttons: [
                        {
                            text: _t("Launch webcam"), classes: 'btn btn-primary capture-button',
                            click: function () {
                                navigator.mediaDevices.getUserMedia({
                                    video: {width: {max: 320}, height: {max: 240}}
                                }).then(function (stream) {
                                    videostream = stream;
                                    video = document.querySelector('#screenshot video');
                                    video.srcObject = videostream;
                                    canvas = document.createElement('canvas');
                                    canvas.style = 'display:none;';
                                    img = document.querySelector('#screenshot-img');
                                }).catch(function (error) {
                                    alert("Error with webcam : " + error);
                                });
                            }
                        },
                        {
                            text: _t("Take screenshot"), classes: 'btn btn-primary screenshot-button',
                            click:
                                function () {
                                    canvas.width = video.videoWidth;
                                    canvas.height = video.videoHeight;
                                    canvas.getContext('2d').drawImage(video, 0, 0);
                                    // Other browsers will fall back to image/png
                                    img.src = canvas.toDataURL('image/png');
                                    $('.save_close_btn').removeAttr('disabled');
                                    videostream.getTracks()[0].stop();
                                }
                        },
                        {
                            text: _t("Save & Close"), classes: 'btn-primary save_close_btn', close: true,
                            click:
                                function () {
                                    var img_data_base64 = img.src.split(',')[1],
                                        ctx = {},
                                        model = false,
                                        id = false;
                                    // Upload image in Binary Field
                                    if (sidebar_instance.getParent() === undefined) {
                                        ctx = sidebar_instance.view.ViewManager.ActionManager.action_context.context;
                                        id = ctx.active_id;
                                        model = ctx.active_model;
                                    } else {
                                        id = sidebar_instance.getParent().get_selected_ids()[0];
                                        model = sidebar_instance.getParent().dataset.model;
                                    }
                                    var AttachmentObj = new Model('ir.attachment');
                                    return AttachmentObj.call('create', [{
                                        'name': 'web-cam-screenshot.jpeg',
                                        'res_model': model,
                                        'res_id': id,
                                        'datas': img_data_base64,
                                    }]).then(function (result) {
                                        var dom = [['res_model', '=', model], ['res_id', '=', id], ['type', 'in', ['binary', 'url']]];
                                        var ds = new data.DataSetSearch(sidebar_instance, 'ir.attachment', ctx, dom);
                                        ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(sidebar_instance.on_attachments_loaded);
                                    })
                                }
                        },
                        {
                            text: _t("Close"), close: true
                        }
                    ]
                }).open();
                $('.save_close_btn').attr('disabled', 'disabled');
                WebCamDialog.find("#screenshot-img").attr({'src': "/web_widget_image_webcam/static/src/img/webcam_placeholder.png"});
            });
        }
    });

    Dialog.include({
        destroy: function () {
            if (videostream !== undefined) {
                videostream.getTracks()[0].stop();            }
            this._super.apply(this, arguments);
        }
        ,
    });

});