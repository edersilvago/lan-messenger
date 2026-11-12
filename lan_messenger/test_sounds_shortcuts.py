"""Teste de sons + atalhos (sem áudio real). Roda: python -m lan_messenger.test_sounds_shortcuts"""
from __future__ import annotations

import tempfile

from . import profile
from .app_gui import send_binding_allows
from . import sfx


def main() -> None:
    # 1. teclas de envio
    assert send_binding_allows("Return", "enter") is True
    assert send_binding_allows("Control-Return", "enter") is False
    assert send_binding_allows("Return", "ctrl_enter") is False
    assert send_binding_allows("Control-Return", "ctrl_enter") is True
    print("OK send_binding_allows (Enter x Ctrl+Enter)")

    # 2. hotkeys
    assert sfx.parse_hotkey("Ctrl + Shift + S") == "<Control-Shift-s>"
    assert sfx.parse_hotkey("Ctrl+Enter") is None  # Enter não suportado como hotkey global
    assert sfx.parse_hotkey("Ctrl + F5") == "<Control-F5>"
    assert sfx.parse_hotkey("banana") is None
    assert sfx.parse_hotkey("S") is None
    print("OK parse_hotkey")

    # 3. sons: desabilitado nunca emite; sem winsound nunca quebra
    tmp = tempfile.mkdtemp()
    pf, sf = profile._paths(None)  # caminho padrão não pode levantar (bug real)
    assert pf.name == "profile.json" and sf.name == "settings.json"
    _, s = profile.load(base=tmp)
    assert s.sounds_enabled is False and s.send_key == "enter"
    assert sfx.play(s, "message") is False
    s.sounds_enabled = True
    s.snd_message = False
    assert sfx.play(s, "message") is False
    s.snd_message = True
    assert sfx.play(s, "message") is True  # emite em thread (no-op fora do Windows)
    assert sfx.play(s, "evento-inexistente") is False
    s.send_key = "ctrl_enter"
    s.bring_hotkey = "Ctrl + Shift + S"
    profile.save(profile.Profile(), s, base=tmp)
    _, s2 = profile.load(base=tmp)
    assert s2.send_key == "ctrl_enter" and s2.bring_hotkey == "Ctrl + Shift + S"
    assert s2.snd_repeat_sec == 5
    print("OK sfx.play + persistência sons/atalhos")
    print("TESTE SOUNDS SHORTCUTS: PASSOU")


if __name__ == "__main__":
    main()
