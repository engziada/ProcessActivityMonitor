# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.ini', '.'),
    ],
    hiddenimports=[
        # From requirements.txt
        'altgraph',
        'colorama',
        'fpdf',
        'greenlet',
        'keyboard',
        'markdown_it_py',
        'mdurl',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils', 'openpyxl.workbook', 'openpyxl.worksheet',
        'packaging',
        'pefile',
        'psutil',
        'pyarmor',
        'pygetwindow',
        'pygments', 'pygments.lexers', 'pygments.formatters', 'pygments.styles',
        'pyinstaller',
        'pyinstaller_hooks_contrib',
        'pynput', 'pynput.keyboard', 'pynput.mouse',
        'pyrect',
        'win32gui', 'win32process', 'win32api', 'win32con',
        'pywin32_ctypes',

        # Rich and all its submodules
        'rich', 'rich.prompt', 'rich.panel', 'rich.text', 'rich.align', 'rich.console',
        'rich.layout', 'rich.table', 'rich.live', 'rich.box',
        'rich.style', 'rich.theme', 'rich.color', 'rich.markup', 'rich.measure',
        'rich.segment', 'rich.columns', 'rich.pretty', 'rich.logging', 'rich.progress',
        'rich.traceback', 'rich.syntax', 'rich.tree', 'rich.rule', 'rich.spinner',
        'rich.filesize', 'rich.highlighter', 'rich.json', 'rich.padding',

        # SQLAlchemy and its submodules
        'sqlalchemy', 'sqlalchemy.ext.declarative', 'sqlalchemy.orm', 'sqlalchemy.sql',
        'sqlalchemy.engine', 'sqlalchemy.dialects', 'sqlalchemy.dialects.sqlite',

        # Typing extensions
        'typing_extensions',

        # Six (commonly used utility)
        'six',

        # Standard library modules that might be used
        'datetime', 'time', 'os', 'sys', 'threading', 'contextlib', 'configparser',

        # Your application modules
        'models', 'console_utils', 'export_utils', 'config_editor', 'query_logs', 'trial_license_manager'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ProcessActivityMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
