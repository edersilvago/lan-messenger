"""Regressões observadas após implantação ampla.

Roda: python -m lan_messenger.test_production_fixes
"""
from __future__ import annotations

import ctypes
from types import SimpleNamespace

from . import app_gui


def main() -> None:
    groups_a = {
        "TI": [("10.0.0.1", {"status": "online"})],
        "RH": [("10.0.0.2", {"status": "offline"})],
    }
    groups_b = {
        "TI": [("10.0.0.1", {"status": "away"})],
        "RH": [("10.0.0.2", {"status": "online"})],
    }
    sig_a = app_gui.roster_layout_signature(groups_a, ["TI", "RH"], set())
    sig_b = app_gui.roster_layout_signature(groups_b, ["TI", "RH"], set())
    assert sig_a == sig_b, (sig_a, sig_b)
    groups_b["TI"].append(("10.0.0.3", {"status": "online"}))
    assert app_gui.roster_layout_signature(groups_b, ["TI", "RH"], set()) != sig_a
    print("OK presença atualiza linhas sem reconstruir toda a lista")

    x, y = app_gui.center_in_area(650, 620, (1920, 0, 3840, 1040))
    assert (x, y) == (2555, 210), (x, y)
    print("OK conversa centraliza no monitor da janela principal")

    rows = list(range(100))
    batch, next_index = app_gui.take_history_batch(rows, 0, 12)
    assert batch == list(range(12)) and next_index == 12
    print("OK histórico pode renderizar em lotes sem bloquear abertura")

    class Store:
        def __init__(self, inserted: bool):
            self.inserted = inserted

        def add_message_once(self, *_args):
            return self.inserted

    class Win:
        def winfo_exists(self):
            return True

    class Chat:
        def __init__(self):
            self.win = Win()
            self.focused = False
            self.calls = []

        def incoming(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    def make_app(inserted: bool, behavior: str = "foreground"):
        app = SimpleNamespace()
        app.store = Store(inserted)
        app.settings = SimpleNamespace(
            incoming_behavior=behavior, log_enabled=False,
            snd_msg_mode="background", snd_repeat=False,
            sounds_enabled=False)
        app.chat_windows = {}
        app._group_window_for = lambda _ip: None
        app.peer_label = lambda _ip: "Ana"
        app.selected_info = lambda _ip: {"display": "Ana", "status": "online"}
        app.touch = lambda: None
        app._in_tray = False
        app.tray = None
        app.opened = []
        app.flashed = []

        def open_chat(ip, minimized=False):
            app.opened.append((ip, minimized))
            app.chat_windows[ip] = Chat()

        app.open_chat = open_chat
        app._flash_chat_window = lambda chat: app.flashed.append(chat)
        return app

    duplicate = make_app(False)
    app_gui.App._on_msg(duplicate, {"id": "m1", "text": "oi"}, "10.0.0.2")
    assert duplicate.chat_windows == {}

    fresh = make_app(True)
    app_gui.App._on_msg(fresh, {"id": "m2", "text": "nova"}, "10.0.0.2")
    calls = fresh.chat_windows["10.0.0.2"].calls
    assert len(calls) == 1 and calls[0][1]["append_history"] is False, calls
    print("OK reentrega e primeira abertura não duplicam mensagem")

    minimized = make_app(True, behavior="minimize")
    app_gui.App._on_msg(minimized, {"id": "m3", "text": "abre"}, "10.0.0.3")
    assert "10.0.0.3" in minimized.chat_windows
    min_calls = minimized.chat_windows["10.0.0.3"].calls
    assert minimized.opened == [("10.0.0.3", True)], minimized.opened
    assert len(min_calls) == 1 and min_calls[0][1]["announce"] is False
    assert minimized.flashed == [minimized.chat_windows["10.0.0.3"]]
    print("OK modo foco cria conversa minimizada e somente pisca")

    existing = make_app(True, behavior="minimize")
    existing_chat = Chat()
    existing.chat_windows["10.0.0.4"] = existing_chat
    app_gui.App._on_msg(existing, {"id": "m4", "text": "pisca"}, "10.0.0.4")
    assert existing.opened == []
    assert existing_chat.calls[0][1]["announce"] is False
    assert existing.flashed == [existing_chat]
    print("OK modo foco não traz conversa existente ao primeiro plano")

    activated = []
    flashed = []
    real_flash = app_gui.flash_window
    announce = SimpleNamespace()
    announce.app = SimpleNamespace(
        _activate_chat_window=lambda chat: activated.append(chat))
    announce.win = object()
    announce.focused = False
    app_gui.flash_window = lambda win: flashed.append(win) or True
    try:
        app_gui.ChatWindow._announce(announce)
    finally:
        app_gui.flash_window = real_flash
    assert activated == [announce] and flashed == [announce.win]
    print("OK mensagem traz conversa à frente e pisca na barra")

    class WinCall:
        def __init__(self, result):
            self.result = result
            self.calls = []
            self.restype = None

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    get_ancestor = WinCall(9001)
    flash = WinCall(1)
    fake_windll = SimpleNamespace(user32=SimpleNamespace(
        GetAncestor=get_ancestor, FlashWindowEx=flash))
    real_windll = ctypes.windll
    ctypes.windll = fake_windll
    try:
        assert app_gui.flash_window(SimpleNamespace(winfo_id=lambda: 1234))
    finally:
        ctypes.windll = real_windll
    info = flash.calls[0][0]._obj
    assert get_ancestor.calls == [(1234, 2)], get_ancestor.calls
    assert info.hwnd == 9001 and info.dwFlags == 15 and info.uCount == 0, (
        info.hwnd, info.dwFlags, info.uCount)
    print("OK pisca botão raiz até usuário abrir a conversa")

    print("TESTE PRODUCTION FIXES: PASSOU")


if __name__ == "__main__":
    main()
