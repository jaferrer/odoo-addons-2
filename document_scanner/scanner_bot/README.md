## COMPILATION DU BOT
# Requirement

PyScanLib du repo ndp-systeme

Pillow

PyPDF2

# PyScanLib
Exécuter ces commandes pour pouvoir compiler le bot

```git clone git@github.com:ndp-systemes/pyScanLib.git```

Ou

```git clone https://github.com/ndp-systemes/pyScanLib.git```

puis aller dans le répertoire pyScanLib

```cd pyScanLib```

et la compiler

```python setup.py install```

Ensuite la compilation devrai être ok

# Création du msi (Installer)
aller dans dans le repertoire ```document_scanner/scanner_bot```

et exécuter cette commande
```python setup.py bdist_msi```

# Le Bot et ces fichiers
**scanner.ini** dans le répertoire *$APP_DATA$/Roaming/document_scanner*

les fichiers de log sont dans le répertoire *$APP_DATA$/Local/Temp/scanner_bot/log*
au format log_YYYYmmdd.log 