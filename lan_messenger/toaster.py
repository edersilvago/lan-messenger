"""Notificações do sistema (toast) — Win10/11 via windows-toasts.

Fallback: quem chama (app_gui) usa o balão da bandeja quando este módulo
não consegue enviar (Win7/8.1, biblioteca ausente ou falha de envio).
O windows-toasts não é instalado no Python 3.8 (build Win7) — o import
falha e o app segue sem toast, sem travar.
"""
from __future__ import annotations

try:  # pragma: no cover - disponível só no build Win10/11 (py3.13)
    from windows_toasts import Toast, WindowsToaster
except Exception:  # ImportError ou falha de WinRT
    Toast = None
    WindowsToaster = None

_toaster = None  # instância única por app_id


def supports_toast() -> bool:
    """True quando a biblioteca de toast está disponível (Win10/11)."""
    return WindowsToaster is not None


def notify(title: str, message: str, on_click=None) -> bool:
    """Envia um toast do Windows. True = enviado; False = use o fallback.

    on_click: callback disparado quando o usuário clica na notificação
    (roda em thread do WinRT — quem chama deve reencaminhar para a UI).
    """
    if WindowsToaster is None:
        return False
    global _toaster
    try:
        if _toaster is None:
            _toaster = WindowsToaster("LAN Messenger")
        n = Toast(text_fields=[title, message])
        if on_click is not None:
            n.on_activated = lambda *_a, **_k: on_click()
        _toaster.show_toast(n)
        return True
    except Exception:
        return False
