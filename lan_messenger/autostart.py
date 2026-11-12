"""Autostart no Windows (HKCU ...\\Run). Sem admin: chave por usuário."""
from __future__ import annotations

import sys

try:
    import winreg
    HAVE_WINREG = True
except ImportError:  # não-Windows
    winreg = None  # type: ignore[assignment]
    HAVE_WINREG = False

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "LANMessenger"


def default_command() -> str:
    """Comando registrado. No .exe (frozen) usa o próprio executável."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m lan_messenger'


def enable(command: str | None = None, name: str = APP_NAME) -> None:
    if not HAVE_WINREG:
        raise OSError("autostart só suportado no Windows")
    assert winreg is not None
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, command or default_command())


def disable(name: str = APP_NAME) -> None:
    if not HAVE_WINREG:
        return
    assert winreg is not None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass


def is_enabled(name: str = APP_NAME) -> bool:
    return current(name) is not None


def current(name: str = APP_NAME) -> str | None:
    if not HAVE_WINREG:
        return None
    assert winreg is not None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            value, _ = winreg.QueryValueEx(k, name)
            return str(value)
    except FileNotFoundError:
        return None
