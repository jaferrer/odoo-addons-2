.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl.html
   :alt: License: LGPL-3

====================
MFA Support via TOTP
====================

This module adds support for MFA using TOTP (time-based, one-time passwords)
for the specific use case where :

- Users usually connect from a list of known IPs (e.g. their company IPs), and should be able to do so without MFA.
- Selected users can connect from other IPs (e.g. roaming users), and MFA must be active for them.
- Other users are not allowed to connect from other IPs and should be simply blocked

This module is based on OCA's `auth_totp` module.

Installation
============

1. Install the PyOTP library using pip: ``pip install pyotp``
2. Follow the standard module install process

Configuration
=============

By default, the trusted device cookies introduced by this module have a 
``Secure`` flag. This decreases the likelihood of cookie theft via
eavesdropping but may result in cookies not being set by certain browsers
unless your Odoo instance uses HTTPS. If necessary, you can disable this flag
by going to ``Settings > Parameters > System Parameters`` and changing the
``auth_totp.secure_cookie`` key to ``0``.

Usage
=====

If necessary, a user's trusted devices can be revoked by disabling and
re-enabling MFA for that user.
