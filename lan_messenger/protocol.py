"""Protocolo JSON com framing length-prefixed (4 bytes big-endian)."""
from __future__ import annotations

import json
import socket
import struct
import time
import uuid

from . import config

HEADER = struct.Struct("!I")


def encode_frame(obj: dict) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False).encode(config.ENCODING)
    return HEADER.pack(len(payload)) + payload


def _recv_exact(sock: socket.socket, n: int, timeout: float = 10.0) -> bytes:
    sock.settimeout(timeout)
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("conexao fechada no meio do frame")
        buf += chunk
    return bytes(buf)


def recv_frame(sock: socket.socket, timeout: float = 10.0) -> dict:
    raw_len = _recv_exact(sock, HEADER.size, timeout)
    (size,) = HEADER.unpack(raw_len)
    if size > 50 * 1024 * 1024:  # 50MB: protege de frame malformado
        raise ValueError(f"frame grande demais: {size}")
    payload = _recv_exact(sock, size, timeout)
    return json.loads(payload.decode(config.ENCODING))


def send_frame(sock: socket.socket, obj: dict, timeout: float = 10.0) -> None:
    sock.settimeout(timeout)
    sock.sendall(encode_frame(obj))


def make_beacon(name: str, user: str, status: str = "online",
                display: str = "", dept: str = "Geral", role: str = "",
                anydesk: str = "", rustdesk: str = "",
                cpu: str = "", ram: str = "", ram_type: str = "", disk: str = "",
                os_info: str = "", status_msg: str = "",
                app_version: str = "") -> dict:
    return {"type": "beacon", "name": name, "user": user,
            "status": status, "display": display or name,
            "dept": dept or "Geral", "role": role or "",
            "anydesk": anydesk or "", "rustdesk": rustdesk or "",
            "cpu": cpu or "", "ram": ram or "", "ram_type": ram_type or "",
            "disk": disk or "", "os": os_info or "",
            "status_msg": status_msg or "", "app_version": app_version or "",
            "ts": time.time()}


def make_ping(name: str, user: str) -> dict:
    """Sonda de descoberta: quem recebe responde com beacon unicast imediato."""
    return {"type": "ping", "name": name, "user": user, "ts": time.time()}


def make_hello(name: str, user: str) -> dict:
    """Sonda de presença via TCP: o chat responde com o beacon (fallback
    quando o UDP está bloqueado na VPN)."""
    return {"type": "hello", "name": name, "user": user, "ts": time.time()}


def make_msg(from_name: str, from_user: str, text: str, to: str = "",
             bcast: bool = False, msg_id: str = "") -> dict:
    return {"type": "msg", "id": msg_id or uuid.uuid4().hex, "from_name": from_name,
            "from_user": from_user, "to": to, "text": text,
            "bcast": bcast, "ts": time.time()}


def make_ack(msg_id: str) -> dict:
    return {"type": "ack", "id": msg_id, "ts": time.time()}


def make_file_header(from_name: str, filename: str, size: int, sha256: str) -> dict:
    return {"type": "file-header", "id": uuid.uuid4().hex, "from_name": from_name,
            "filename": filename, "size": size, "sha256": sha256, "ts": time.time()}


def make_file_ack(file_id: str, ok: bool = True, error: str = "") -> dict:
    return {"type": "file-ack", "id": file_id, "ok": ok, "error": error,
            "ts": time.time()}
