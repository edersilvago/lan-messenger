"""Teste de tooltips, flash e barra de ícones. Roda: python -m lan_messenger.test_toolbar"""
from __future__ import annotations

from pathlib import Path

from .app_gui import TOOLBAR_BUTTONS, flash_window


def main() -> None:
    assert len(TOOLBAR_BUTTONS) == 8, len(TOOLBAR_BUTTONS)
    tips = [t for _, t, _, _ in TOOLBAR_BUTTONS]
    assert tips == ["Conversa", "Mensagem em massa", "Arquivos recebidos",
                    "Histórico", "Minhas informações", "Rede",
                    "Configurações", "Ajuda e Sobre"], tips
    for _, _, method, icon in TOOLBAR_BUTTONS:
        p = Path(__file__).parent / "assets" / icon
        assert p.is_file() and p.stat().st_size > 500, f"ícone ausente: {icon}"
    assert len({i for _, _, _, i in TOOLBAR_BUTTONS}) == 8  # sem repetir

    class Dummy:
        def winfo_id(self):
            raise RuntimeError("sem janela")
    assert flash_window(Dummy()) is False  # nunca levanta
    print("OK 8 atalhos com ícones + flash seguro")
    print("TESTE TOOLBAR: PASSOU")


if __name__ == "__main__":
    main()
