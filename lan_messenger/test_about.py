"""Teste de Sobre/Ajuda/ícone. Roda: python -m lan_messenger.test_about"""
from __future__ import annotations

from pathlib import Path

from . import config
from .app_gui import HELP_TEXT


def main() -> None:
    assert config.APP_NAME == "LAN Messenger"
    assert config.APP_VERSION.startswith("1."), config.APP_VERSION
    ico = Path(__file__).parent / "assets" / "app.ico"
    assert ico.is_file() and ico.stat().st_size > 1000, "app.ico ausente"
    assert config.asset_path("app.ico") == str(ico)
    assert config.asset_path("nao-existe.xyz") is None
    assert len(HELP_TEXT) > 200 and "Rede" in HELP_TEXT
    print("OK versão + ícone + ajuda")
    print("TESTE ABOUT: PASSOU")


if __name__ == "__main__":
    main()
