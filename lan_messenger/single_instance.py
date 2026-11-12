"""Trava de instância única: impede 2 cópias do app no mesmo PC.

No Windows, SO_REUSEADDR permite dois processos dividirem a mesma porta,
então a trava usa porta dedicada 127.0.0.1:50009 com SO_EXCLUSIVEADDRUSE.
Segunda instância recebe None e deve avisar + sair.
"""
from __future__ import annotations

import socket

LOCK_PORT = int(__import__("os").getenv("LAN_LOCK_PORT", "50009"))


def acquire() -> socket.socket | None:
    """Tenta a trava. Retorna o socket (segure-o!) ou None se já há dono."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def release(sock: socket.socket | None) -> None:
    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass
