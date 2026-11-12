"""Sons do Windows via winsound (stdlib) — tela Eventos de Som clássica.

Sem arquivos .wav: cada evento tem um padrão de beeps. Fora do Windows
ou com sons desabilitados, play() é no-op e retorna False.
"""
from __future__ import annotations

import threading

from . import config

try:
    import winsound  # type: ignore[import-not-found]
except ImportError:  # Linux/macOS
    winsound = None  # type: ignore[assignment]

# evento -> [(frequência Hz, duração ms, pausa ms)]
PATTERNS: dict[str, list[tuple[int, int, int]]] = {
    "message": [(880, 150, 0)],
    "broadcast": [(660, 150, 100), (880, 200, 0)],
    "user_online": [(520, 120, 80), (780, 150, 0)],
    "file": [(990, 120, 80), (990, 120, 0)],
}

SOUND_FILES = {
    "message": "sounds/Message.wav",
    "broadcast": "sounds/Broadcast.wav",
    "user_online": "sounds/Online.wav",
    "file": "sounds/File.wav",
}

_EVENT_FLAG = {
    "message": "snd_message",
    "broadcast": "snd_broadcast",
    "user_online": "snd_user_online",
    "file": "snd_file",
}


def _emit(which: str) -> None:
    if winsound is None:
        return
    try:
        wav = SOUND_FILES.get(which)
        path = config.asset_path(wav) if wav else None
        if path:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        for freq, dur, gap in PATTERNS.get(which, []):
            winsound.Beep(freq, dur)
            if gap:
                import time
                time.sleep(gap / 1000)
    except RuntimeError:
        pass  # dispositivo de som indisponível


def play(settings, which: str) -> bool:
    """Toca o som do evento se habilitado. Retorna True se emitiu."""
    if not getattr(settings, "sounds_enabled", False):
        return False
    flag = _EVENT_FLAG.get(which)
    if flag and not getattr(settings, flag, True):
        return False
    if which not in PATTERNS:
        return False
    threading.Thread(target=_emit, args=(which,), daemon=True).start()
    return True


def parse_hotkey(spec: str) -> str | None:
    """'Ctrl + Shift + S' -> '<Control-Shift-s>' (evento Tk). None se inválido.

    Aceita modificadores Ctrl/Shift/Alt + tecla (A-Z, 0-9 ou F1-F12).
    """
    parts = [p.strip().lower() for p in spec.split("+")]
    if len(parts) < 2:
        return None
    mods = {"ctrl": "Control", "shift": "Shift", "alt": "Alt"}
    *mod_parts, key = parts
    if not mod_parts or any(m not in mods for m in mod_parts):
        return None
    if len(key) == 1 and (key.isalnum()):
        key_str = key.lower() if len(key) == 1 and key.isalpha() else key
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        key_str = key.capitalize()
    else:
        return None
    # remove modificadores duplicados preservando ordem
    seen: list[str] = []
    for m in mod_parts:
        if mods[m] not in seen:
            seen.append(mods[m])
    return f"<{'-'.join(seen + [key_str])}>"
