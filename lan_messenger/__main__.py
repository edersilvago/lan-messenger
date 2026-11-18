"""Ponto de entrada: python -m lan_messenger (equivale a app_gui).

Import absoluto de propósito: o PyInstaller executa este arquivo como
script top-level, onde import relativo falharia.
"""
import sys
import threading

from lan_messenger.app_gui import log_crash, main


def _hook(tp, exc, tb) -> None:
    """Exceção não capturada (inclusive antes da UI): grava em logs/crash.log."""
    log_crash("uncaught", exc)
    sys.__excepthook__(tp, exc, tb)


def _thread_hook(args) -> None:
    """Exceção em thread de trabalho (descoberta, chat, arquivos): idem."""
    log_crash(f"thread {getattr(args.thread, 'name', '?')}", args.exc_value)


if __name__ == "__main__":
    sys.excepthook = _hook
    threading.excepthook = _thread_hook
    main()
