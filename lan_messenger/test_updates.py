"""Teste da v1.37: aviso de nova versão. Roda: python -m lan_messenger.test_updates"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from . import app_gui, updates


class Response:
    def __init__(self, data: dict):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.data).encode("utf-8")


def main() -> None:
    assert updates.version_tuple("v1.37") == (1, 37)
    assert updates.version_tuple("1.37.2") == (1, 37, 2)
    assert updates.version_tuple("lixo") == ()
    assert updates.is_newer("v1.37", "1.36")
    assert not updates.is_newer("v1.36", "1.36")
    assert not updates.is_newer("lixo", "1.36")
    print("OK comparação de versões")

    def newer(_request, timeout=0):
        assert timeout == 4.0
        return Response({
            "tag_name": "v1.38",
            "html_url": "https://github.com/edersilvago/lan-messenger/releases/tag/v1.38",
        })

    got = updates.check_latest("1.37", opener=newer)
    assert got == (
        "1.38",
        "https://github.com/edersilvago/lan-messenger/releases/tag/v1.38",
    ), got

    same = lambda *_a, **_k: Response({
        "tag_name": "v1.37", "html_url": updates.RELEASES_URL})
    assert updates.check_latest("1.37", opener=same) is None

    bad_url = lambda *_a, **_k: Response({
        "tag_name": "v2.0", "html_url": "https://example.com/falso"})
    assert updates.check_latest("1.37", opener=bad_url) == (
        "2.0", updates.RELEASES_URL)

    def broken(*_a, **_k):
        raise OSError("sem internet")

    assert updates.check_latest("1.37", opener=broken) is None
    print("OK consulta, URL segura e falha offline silenciosa")

    # Aviso inicial oferece instalação direta, sem abrir página do site.
    prompts = []
    started = []
    old_ask = app_gui.messagebox.askyesno
    app_gui.messagebox.askyesno = lambda title, text, **_kw: (
        prompts.append((title, text)) or True)
    app = SimpleNamespace()
    app.root = object()
    app._update_available = None
    app.statusbar = SimpleNamespace(configure=lambda **_kw: None)
    app._start_update = lambda version, url: started.append((version, url))
    try:
        app_gui.App._offer_update(
            app, "1.46",
            "https://github.com/edersilvago/lan-messenger/releases/tag/v1.46")
    finally:
        app_gui.messagebox.askyesno = old_ask
    assert "Quer atualizar a sua versão agora?" in prompts[0][1], prompts
    assert "página de Releases" not in prompts[0][1]
    assert started == [(
        "1.46",
        "https://github.com/edersilvago/lan-messenger/releases/tag/v1.46")]
    print("OK aviso oferece atualização direta")

    script = app_gui.update_helper_script(
        r"C:\Temp\LAN Messenger Setup.exe",
        r"C:\Program Files\LANMessenger\LANMessenger.exe",
        r"C:\Temp\lan-update.ready")
    assert '> "C:\\Temp\\lan-update.ready" echo ready' in script
    assert "taskkill /F /IM LANMessenger.exe" in script
    assert ('start /wait "" "C:\\Temp\\LAN Messenger Setup.exe" '
            "/SILENT /SUPPRESSMSGBOXES /NORESTART "
            '/LOG="C:\\Temp\\LAN Messenger Setup.exe.log"') in script
    assert "/VERYSILENT" not in script
    assert ('start "" "C:\\Program Files\\LANMessenger\\LANMessenger.exe"'
            in script)
    assert ('if "%INSTALL_EXIT%"=="0" del /F /Q '
            '"C:\\Temp\\LAN Messenger Setup.exe"' in script)
    print("OK auxiliar encerra, instala, reabre e limpa")

    args = app_gui.update_helper_args(r"C:\Temp\lan-update.cmd")
    assert args[-3:] == ["/d", "/c", r"C:\Temp\lan-update.cmd"], args
    print("OK auxiliar inicia separado do LAN Messenger")

    with tempfile.TemporaryDirectory(prefix="lan update ") as tmp:
        marker = Path(tmp) / "started.txt"
        helper = Path(tmp) / "update helper.cmd"
        helper.write_text(
            f'@echo off\r\n> "{marker}" echo started\r\n',
            encoding="mbcs")
        result = subprocess.run(
            app_gui.update_helper_args(str(helper)),
            timeout=10, check=False)
        assert result.returncode == 0 and marker.is_file(), result.returncode
    print("OK auxiliar executa quando caminho contém espaços")

    base = Path(__file__).parent
    for name in ("installer_win10_11.iss", "installer_win7_81.iss"):
        script = (base / name).read_text(encoding="utf-8")
        assert "CloseApplications=no" in script, name
        assert "'/T /F /IM {#MyAppExe}'" in script, name
    print("OK instaladores evitam diálogo e encerram toda a árvore do app")

    print("TESTE UPDATES: PASSOU")


if __name__ == "__main__":
    main()
