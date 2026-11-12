"""Log em arquivos texto (tela Log clássica).

- Habilitar/desabilitar via settings.log_enabled.
- "single": um arquivo lan_messages.log.
- "per_user": um <contato>.log por usuário (+ subpasta opcional por usuário).
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

from . import profile as profile_mod


def safe_name(label: str) -> str:
    name = _SAFE.sub("_", label.strip()).strip("._") or "contato"
    return name[:80]


def base_dir(settings) -> Path:
    if getattr(settings, "log_dir", ""):
        return Path(settings.log_dir)
    from . import config as _config
    return _config.APP_DATA / "logs"


def target_for(settings, peer_label: str) -> Path:
    base = base_dir(settings)
    if getattr(settings, "log_mode", "single") == "per_user":
        if getattr(settings, "log_user_subdir", False):
            d = base / safe_name(peer_label)
            d.mkdir(parents=True, exist_ok=True)
            return d / f"{safe_name(peer_label)}.log"
        base.mkdir(parents=True, exist_ok=True)
        return base / f"{safe_name(peer_label)}.log"
    base.mkdir(parents=True, exist_ok=True)
    return base / "lan_messages.log"


def log_message(settings, peer_label: str, direction: str, text: str) -> Path | None:
    """Acrescenta uma linha ao log. Retorna o arquivo ou None (desabilitado)."""
    if not getattr(settings, "log_enabled", True):
        return None
    dest = target_for(settings, peer_label)
    ts = time.strftime("%d/%m/%Y - %H:%M:%S")
    tag = "Outgoing" if direction == "out" else "Incoming"
    try:
        with open(dest, "a", encoding="utf-8") as f:
            f.write(f"{ts} ({tag}): {text}\n")
    except OSError:
        return None
    return dest


def log_file_event(settings, peer_label: str, direction: str, filename: str) -> Path | None:
    return log_message(settings, peer_label, direction, f"[arquivo] {filename}")


def load_settings(base=None):
    return profile_mod.load(base)[1]
