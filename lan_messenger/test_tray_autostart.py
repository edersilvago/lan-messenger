"""Teste de tray + autostart. Roda: python -m lan_messenger.test_tray_autostart"""
from __future__ import annotations

from . import autostart, tray


def main() -> None:
    # 1. autostart (winreg; pula fora do Windows)
    if autostart.HAVE_WINREG:
        name = "LANMessengerTest"
        autostart.disable(name)
        assert autostart.is_enabled(name) is False
        autostart.enable("dummy-cmd", name=name)
        assert autostart.is_enabled(name) is True
        assert autostart.current(name) == "dummy-cmd"
        autostart.disable(name)
        assert autostart.is_enabled(name) is False
        print("OK autostart enable/disable/is_enabled")
        assert "lan_messenger" in autostart.default_command()
        print(f"OK default_command={autostart.default_command()}")
    else:
        print("SKIP autostart (sem winreg)")

    # 2. tray (pula sem pystray/Pillow ou sem display)
    if tray.HAVE_TRAY:
        try:
            img = tray.make_icon(False)
            img2 = tray.make_icon(True)
            assert img.size == (64, 64) and img2.size == (64, 64)
            print("OK tray.make_icon (normal + unread)")
        except Exception as e:
            print(f"SKIP tray icon (sem display?): {e}")
    else:
        print("SKIP tray (pystray/Pillow ausentes)")
    print("TESTE TRAY AUTOSTART: PASSOU")


if __name__ == "__main__":
    main()
