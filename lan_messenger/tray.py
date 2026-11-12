"""Bandeja do sistema (tray) via pystray. Degrada sem a dependência."""
from __future__ import annotations

from collections.abc import Callable

try:
    import pystray
    from PIL import Image, ImageDraw
    HAVE_TRAY = True
except ImportError:
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    HAVE_TRAY = False


def make_icon(unread: bool = False, size: int = 64, base_path: str | None = None):
    """Ícone do tray = app.ico oficial; ponto vermelho = não lida.

    Sem base_path (ou falha), gera o balão verde em código.
    """
    img = None
    if base_path and Image is not None:
        try:
            img = Image.open(base_path).convert("RGBA").resize((size, size))
        except Exception:
            img = None
    if img is None:
        assert Image is not None and ImageDraw is not None
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([6, 10, size - 6, size - 14], fill=(46, 125, 50, 255))
        d.polygon([(18, size - 16), (30, size - 16), (22, size - 4)], fill=(46, 125, 50, 255))
        d.line([14, 26, size - 14, 26], fill="white", width=3)
        d.line([14, 34, size - 14, 34], fill="white", width=3)
    if unread and ImageDraw is not None:
        d = ImageDraw.Draw(img)
        d.ellipse([size - 22, 4, size - 4, 22], fill=(211, 47, 47, 255))
    return img


class TrayController:
    """Ciclo de vida do ícone. run_detached() não bloqueia o Tk."""

    def __init__(self, title: str = "LAN Messenger",
                 on_open: Callable[[], None] | None = None,
                 on_toggle_status: Callable[[], str] | None = None,
                 on_status: Callable[[str], None] | None = None,
                 on_quit: Callable[[], None] | None = None,
                 icon_path: str | None = None):
        if not HAVE_TRAY:
            raise OSError("pystray não instalado (pip install pystray Pillow)")
        assert pystray is not None
        self._unread = False
        self._icon_path = icon_path
        self.icon = pystray.Icon(
            "lan-messenger", make_icon(False, base_path=icon_path), title,
            menu=pystray.Menu(
                # default=True: duplo-clique no tray abre a principal
                pystray.MenuItem("Abrir", lambda i, it: on_open and on_open(),
                                 default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Disponível",
                                 lambda i, it: on_status and on_status("online")),
                pystray.MenuItem("Ocupado",
                                 lambda i, it: on_status and on_status("busy")),
                pystray.MenuItem("Ausente",
                                 lambda i, it: on_status and on_status("away")),
                pystray.MenuItem("Sair", lambda i, it: on_quit and on_quit()),
            ))

    def run(self) -> None:
        self.icon.run_detached()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass

    def set_unread(self, unread: bool) -> None:
        if unread != self._unread:
            self._unread = unread
            try:
                self.icon.icon = make_icon(unread, base_path=self._icon_path)
            except Exception:
                pass

    def notify(self, message: str, title: str = "LAN Messenger") -> None:
        try:
            self.icon.notify(message, title)
        except Exception:
            pass
