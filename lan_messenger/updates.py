"""Consulta leve da versão mais recente no GitHub (sem bloquear a UI)."""
from __future__ import annotations

import json
import urllib.request

API_URL = "https://api.github.com/repos/edersilvago/lan-messenger/releases/latest"
RELEASES_URL = "https://github.com/edersilvago/lan-messenger/releases/latest"


def version_tuple(value: str) -> tuple[int, ...]:
    """'v1.37' -> (1, 37). Valores inválidos viram ()."""
    text = str(value or "").strip().lower().lstrip("v")
    try:
        parts = tuple(int(p) for p in text.split("."))
    except (TypeError, ValueError):
        return ()
    return parts if parts and all(p >= 0 for p in parts) else ()


def is_newer(latest: str, current: str) -> bool:
    """True somente para versão numérica válida e superior."""
    new, old = version_tuple(latest), version_tuple(current)
    return bool(new and old and new > old)


def check_latest(current: str, timeout: float = 4.0,
                 opener=None) -> tuple[str, str] | None:
    """Retorna (versão, URL) se houver atualização; falhas ficam silenciosas."""
    open_url = opener or urllib.request.urlopen
    request = urllib.request.Request(
        API_URL,
        headers={"User-Agent": f"LANMessenger/{current}",
                 "Accept": "application/vnd.github+json"})
    try:
        with open_url(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        tag = str(data.get("tag_name", "")).strip()
        url = str(data.get("html_url", "")).strip()
        if not is_newer(tag, current):
            return None
        if not url.startswith("https://github.com/edersilvago/lan-messenger/"):
            url = RELEASES_URL
        return tag.lstrip("v"), url
    except Exception:
        return None
