odoo.define('backend_theme_menubar', function(require) {
    'use strict';

    var Menu = require('web.Menu');
    var core = require('web.core');
    var Widget = require('web.Widget');

    Menu.include({

        // Force all_outside to prevent app icons from going into more menu
        reflow: function() {
            this._super('all_outside');
        },

        /* Overload to collapse unwanted visible submenus
         * @param allow_open bool Switch to allow submenus to be opened
         */
        open_menu: function(id, allowOpen) {
            this._super(id);
            if (allowOpen) {
                return;
            }
            var $clicked_menu = this.$secondary_menus.find('a[data-menu=' + id + ']');
            $clicked_menu.parents('.oe_secondary_submenu').css('display', '');
        }

    });

    var AppDrawer = Widget.extend({

        /* Provides all features inside of the application drawer navigation.

        Attributes:
            directionCodes (str): Canonical key name to direction mappings.
            deleteCodes
         */

        LEFT: 'left',
        RIGHT: 'right',
        UP: 'up',
        DOWN: 'down',

        // These keys are ignored when presented as single input
        MODIFIERS: [
            'Alt',
            'ArrowDown',
            'ArrowLeft',
            'ArrowRight',
            'ArrowUp',
            'Control',
            'Enter',
            'Escape',
            'Meta',
            'Shift',
            'Tab',
        ],

        isOpen: false,
        keyBuffer: '',
        keyBufferTime: 500,
        keyBufferTimeoutEvent: false,
        dropdownHeightFactor: 0.90,
        initialized: false,

        init: function() {
            this._super.apply(this, arguments);
            this.directionCodes = {
                'left': this.LEFT,
                'right': this.RIGHT,
                'up': this.UP,
                'pageup': this.UP,
                'down': this.DOWN,
                'pagedown': this.DOWN,
                '+': this.RIGHT,
                '-': this.LEFT
            };
            this.initDrawer();
            this.handleWindowResize();
            var $clickZones = $('.odoo_webclient_container, ' +
                'a.oe_menu_leaf, ' +
                'a.oe_menu_toggler, ' +
                'a.oe_logo, ' +
                'i.oe_logo_edit'
            );
            $clickZones.click($.proxy(this.handleClickZones, this));
            core.bus.on('resize', this, this.handleWindowResize);
        },

        // Provides initialization handlers for Drawer
        initDrawer: function() {
            this.$el = $('.drawer');
            this.$el.drawer();
            this.$el.one('drawer.opened', $.proxy(this.onDrawerOpen, this));

            // Setup the iScroll options.
            // You should be able to pass these to ``.drawer``, but scroll freezes.
            this.$el.on(
                'drawer.opened',
                function setIScrollProbes(){
                    var onIScroll = $.proxy(
                        function() {
                            this.iScroll.refresh();
                        },
                        this
                    );
                    // Scroll probe aggressiveness level
                    // 2 == always executes the scroll event except during momentum and bounce.
                    this.iScroll.options.probeType = 2;
                    this.iScroll.on('scroll', onIScroll);
                    // Initialize Scrollbars manually
                    this.iScroll.options.scrollbars = true;
                    this.iScroll.options.fadeScrollbars = true;
                    this.iScroll._initIndicators();
                }
            );
            this.initialized = true;
        },

        // Provides handlers to hide drawer when "unfocused"
        handleClickZones: function() {
            this.$el.drawer('close');
            $('.o_sub_menu_content')
                .parent()
                .collapse('hide');
            $('.navbar-collapse').collapse('hide');
        },

        // Resizes bootstrap dropdowns for screen
        handleWindowResize: function() {
            $('.dropdown-scrollable').css(
                'max-height', $(window).height() * this.dropdownHeightFactor
            );
        },

        /* Performs close actions
         * @fires ``drawer.closed`` to the ``core.bus``
         * @listens ``drawer.opened`` and sends to onDrawerOpen
         */
        onDrawerClose: function() {
            core.bus.trigger('drawer.closed');
            this.$el.one('drawer.opened', $.proxy(this.onDrawerOpen, this));
            this.isOpen = false;
            // Remove inline style inserted by drawer.js
            this.$el.css("overflow", "");
        },

        /* Finds app links and register event handlers
        * @fires ``drawer.opened`` to the ``core.bus``
        * @listens ``drawer.closed`` and sends to :meth:``onDrawerClose``
        */
       onDrawerOpen: function() {
            this.$appLinks = $('.app-drawer-icon-app').parent();
            this.$el.one('drawer.closed', $.proxy(this.onDrawerClose, this));
            core.bus.trigger('drawer.opened');
            this.isOpen = true;
        },

        /* Returns the link adjacent to $link in provided direction.
         * It also handles edge cases in the following ways:
         *   * Moves to last link if LEFT on first
         *   * Moves to first link if PREV on last
         *   * Moves to first link of following row if RIGHT on last in row
         *   * Moves to last link of previous row if LEFT on first in row
         *   * Moves to top link in same column if DOWN on bottom row
         *   * Moves to bottom link in same column if UP on top row
         * @param $link jQuery obj of App icon link
         * @param direction str of direction to go (constants LEFT, UP, etc.)
         * @param $objs jQuery obj representing the collection of links. Defaults
         *  to `this.$appLinks`.
         * @param restrictHorizontal bool Set to true if the collection consists
         *  only of vertical elements.
         * @return jQuery obj for adjacent link
         */
        findAdjacentLink: function($link, direction, $objs, restrictHorizontal) {

            if (_.isUndefined($objs)) {
                $objs = this.$appLinks;
            }

            var obj = [];
            var $rows = restrictHorizontal ? $objs : this.getRowObjs($link, this.$appLinks);

            switch (direction) {
                case this.LEFT:
                    obj = $objs[$objs.index($link) - 1];
                    if (!obj) {
                        obj = $objs[$objs.length - 1];
                    }
                    break;
                case this.RIGHT:
                    obj = $objs[$objs.index($link) + 1];
                    if (!obj) {
                        obj = $objs[0];
                    }
                    break;
                case this.UP:
                    obj = $rows[$rows.index($link) - 1];
                    if (!obj) {
                        obj = $rows[$rows.length - 1];
                    }
                    break;
                case this.DOWN:
                    obj = $rows[$rows.index($link) + 1];
                    if (!obj) {
                        obj = $rows[0];
                    }
                    break;
            }

            if (obj.length) {
                event.preventDefault();
            }

            return $(obj);

        },

        /* Returns els in the same row
         * @param @obj jQuery object to get row for
         * @param $grid jQuery objects representing grid
         * @return $objs jQuery objects of row
         */
        getRowObjs: function($obj, $grid) {
            // Filter by object which middle lies within left/right bounds
            function filterWithin(left, right) {
                return function() {
                    var $this = $(this),
                        thisMiddle = $this.offset().left + $this.width() / 2;
                    return thisMiddle >= left && thisMiddle <= right;
                };
            }
            var left = $obj.offset().left,
                right = left + $obj.outerWidth();
            return $grid.filter(filterWithin(left, right));
        }

    });

    // Init a new AppDrawer when the web client is ready
    core.bus.on('web_client_ready', null, function () {
        new AppDrawer();
    });

    return {
        'AppDrawer': AppDrawer,
    };

});
