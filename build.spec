# build.spec
# Uso:
#   pyinstaller build.spec
#
# Prerequisitos:
#   pip install pyinstaller flet==0.23.2 fpdf2 Pillow pyautogui pywin32
#
# Estructura del proyecto:
#   demo1/
#   ├── main.py
#   ├── build.spec
#   ├── assets/
#   ├── db/
#   │   ├── __init__.py
#   │   └── database.py
#   ├── services/
#   │   ├── __init__.py
#   │   ├── autocomplete_service.py
#   │   ├── invoice_share.py
#   │   └── whatsapp_service.py
#   └── views/
#       ├── __init__.py
#       ├── dashboard.py
#       ├── clientes.py
#       ├── stock_alert.py
#       ├── cuenta_wasi.py
#       ├── facturacion/
#       │   ├── __init__.py
#       │   ├── view.py, controller.py, state.py
#       │   └── components/
#       └── productos/
#           ├── __init__.py
#           ├── stock.py
#           ├── compras.py
#           └── proveedores.py

import sys
from pathlib import Path
import flet

PROJECT_DIR = Path(SPECPATH)
FLET_ASSETS = Path(flet.__file__).parent

datas = [
    (str(FLET_ASSETS / "web"),      "flet/web"),
    (str(FLET_ASSETS / "bin"),      "flet/bin"),
    (str(PROJECT_DIR / "assets"), "assets"),
    (str(PROJECT_DIR / "services" / "invoice_template.html"), "services"),
]

hiddenimports = [
    "flet", "flet_core", "flet_runtime", "flet.fastapi",
    "win32api", "win32con", "win32clipboard", "win32gui", "pywintypes",
    "pyautogui", "pyscreeze", "mouseinfo",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL._imaging",
    "fpdf", "fpdf.svg",
    "sqlite3", "_sqlite3",
    "db.database",
    "services.autocomplete_service",
    "services.invoice_share",
    "services.whatsapp_service",
    "views.dashboard",
    "views.clientes",
    "views.cuenta_wasi",
    "views.stock_alert",
    "views.facturacion",
    "views.facturacion.view",
    "views.facturacion.controller",
    "views.facturacion.state",
    "views.facturacion.components.autocomplete",
    "views.facturacion.components.item_row",
    "views.productos",
    "views.productos.stock",
    "views.productos.compras",
    "views.productos.proveedores",
    "theme",
]

import site, glob, os
binaries = []
for sp in site.getsitepackages():
    for dll in glob.glob(os.path.join(sp, "pywin32_system32", "*.dll")):
        binaries.append((dll, "."))
    for dll in glob.glob(os.path.join(sp, "win32", "*.pyd")):
        binaries.append((dll, "win32"))

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy",
        "IPython", "jupyter", "notebook", "pytest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MVP_1.0",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python*.dll", "msvcp*.dll"],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python*.dll", "msvcp*.dll"],
    name="MVP_1.0",
)
