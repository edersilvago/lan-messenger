# -*- mode: python ; coding: utf-8 -*-
"""Build do .exe: a partir da RAIZ do projeto rode  lan_messenger\\build_exe.cmd
Gera dist\\LANMessenger.exe (onefile, sem console).
"""
import os
import re

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

try:
    from PyInstaller.utils.hooks import collect_data_files
    _extra_datas = collect_data_files("customtkinter")
except Exception:
    _extra_datas = []


def _exe_version() -> str:
    """Gera o recurso de versão do exe a partir de config.APP_VERSION.

    Controle de versões: botão direito no exe > Propriedades > Detalhes
    sempre mostra a mesma versão da tela Sobre.
    """
    ver = "1.0"
    try:
        with open(os.path.join(ROOT, "lan_messenger", "config.py"),
                  encoding="utf-8") as f:
            m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', f.read())
            if m:
                ver = m.group(1).strip()
    except OSError:
        pass
    parts = [int(p) for p in re.findall(r"\d+", ver)[:4]]
    while len(parts) < 4:
        parts.append(0)
    vtuple = ", ".join(str(p) for p in parts)
    path = os.path.join(ROOT, "lan_messenger", "version_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({vtuple}),
    prodvers=({vtuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'Uso interno'),
          StringStruct('FileDescription', 'LAN Messenger'),
          StringStruct('FileVersion', '{ver}'),
          StringStruct('InternalName', 'LANMessenger'),
          StringStruct('OriginalFilename', 'LANMessenger.exe'),
          StringStruct('ProductName', 'LAN Messenger'),
          StringStruct('ProductVersion', '{ver}')])
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")
    return path

a = Analysis(
    [os.path.join(ROOT, "lan_messenger", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "lan_messenger", "networks.json"), "lan_messenger"),
           (os.path.join(ROOT, "lan_messenger", "assets"), "lan_messenger/assets")]
    + _extra_datas,
    hiddenimports=[],
    hookspath=[],
    excludes=["numpy", "PIL.AvifImagePlugin"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LANMessenger",
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "lan_messenger", "assets", "app.ico"),
    version=_exe_version(),
)
