# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from cx_Freeze import setup, Executable

exe = Executable("odoo_connect.py", shortcutName="Bot Scanner")
shortcut_table = [
    ("DesktopShortcut",  # Shortcut
     "DesktopFolder",  # Directory_
     "Bot Scanner",  # Name
     "TARGETDIR",  # Component_
     "[TARGETDIR]odoo_connect.exe",  # Target
     None,  # Arguments
     None,  # Description
     None,  # Hotkey
     'C:\Windows\System32\imageres.dll',  # Icon
     46,  # IconIndex
     True,  # ShowCmd
     'TARGETDIR'  # WkDir
     ),

    ("StartupShortcut",  # Shortcut
     "StartupFolder",  # Directory_
     "Bot Scanner",  # Name
     "TARGETDIR",  # Component_
     "[TARGETDIR]odoo_connect.exe",  # Target
     None,  # Arguments
     None,  # Description
     None,  # Hotkey
     'C:\Windows\System32\imageres.dll',  # Icon
     46,  # IconIndex
     True,  # ShowCmd
     'TARGETDIR'  # WkDir
     ),

]
bdist_msi_options = {
    'upgrade_code': '{66620F3A-DC3A-11E2-B341-002219E9B01E}',
    'add_to_path': False,
    'initial_target_dir': r'[ProgramFilesFolder]\%s\%s' % ('NDP-SYSTEMES', 'document_scanner'),
    'data': {'Shortcut': shortcut_table}
}
# On appelle la fonction setup
setup(
    name="Robot scanner NDP",
    author="Ndp Systemes",
    maintainer="Ndp Systemes",
    license="GPL.V3",
    version="1.0.0",
    description=u"""
    Bot se connectant au scanner sur le reseau ou en USB
    Ce bot a besoin d'un Odoo avec le module <docuemnt_scanner> d'installé""",
    executables=[exe],
    options={
        'bdist_msi': bdist_msi_options}
)
