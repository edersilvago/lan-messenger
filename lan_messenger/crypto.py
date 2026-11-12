"""Criptografia PSK (AES-256-GCM) para chat e arquivos.

Modelo: chave pré-compartilhada (PSK) igual em todos os PCs, cadastrada na
tela Rede e distribuída pelo admin (GPO/pendrive). Sem a mesma chave, peers
não se entendem — documentado no README.

- Chat: o JSON da mensagem é selado (nonce aleatório por mensagem).
- Arquivos: header segue em claro (nome/tamanho visíveis na rede!); cada
  bloco de 64KB é selado com nonce = sha256(file_id)[:8] + contador.
- Beacons de discovery seguem em claro (só presença/nome/departamento).
- Sem chave configurada: tráfego em claro (statusbar avisa).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config, protocol

ENC_MARKER = "__enc__"
TAG_LEN = 16


class CryptoError(Exception):
    """Ex: peer usa criptografia e não temos a chave (ou vice-versa)."""


def generate_key() -> str:
    """Nova PSK aleatória (base64). Distribua o mesmo valor a todos os PCs."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


def parse_key(s: str) -> bytes | None:
    """Valida base64 de 32 bytes. None se inválida."""
    try:
        raw = base64.urlsafe_b64decode((s or "").strip())
    except Exception:
        return None
    return raw if len(raw) == 32 else None


def get_key(settings) -> bytes | None:
    return parse_key(getattr(settings, "crypto_key", "") or "")


def send_obj(sock: socket.socket, obj: dict, key: bytes | None,
             timeout: float = 10.0) -> None:
    if key is None:
        protocol.send_frame(sock, obj, timeout=timeout)
        return
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, json.dumps(obj, ensure_ascii=False).encode(config.ENCODING), None)
    protocol.send_frame(sock, {ENC_MARKER: base64.b64encode(nonce + ct).decode("ascii")},
                        timeout=timeout)


def recv_obj(sock: socket.socket, key: bytes | None, timeout: float = 10.0) -> dict:
    frame = protocol.recv_frame(sock, timeout=timeout)
    if ENC_MARKER not in frame:
        return frame
    if key is None:
        raise CryptoError("remetente usa criptografia: configure a mesma chave (Rede)")
    try:
        raw = base64.b64decode(frame[ENC_MARKER])
        nonce, ct = raw[:12], raw[12:]
        plain = AESGCM(key).decrypt(nonce, ct, None)
    except (ValueError, InvalidTag, Exception) as e:
        raise CryptoError(f"falha ao decriptar (chave errada?): {e}") from e
    return json.loads(plain.decode(config.ENCODING))


def _chunk_nonce(file_id: str, counter: int) -> bytes:
    return hashlib.sha256(file_id.encode("utf-8")).digest()[:8] + counter.to_bytes(4, "big")


def seal_chunk(key: bytes, file_id: str, counter: int, data: bytes) -> bytes:
    return AESGCM(key).encrypt(_chunk_nonce(file_id, counter), data, None)


def open_chunk(key: bytes, file_id: str, counter: int, data: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(_chunk_nonce(file_id, counter), data, None)
    except InvalidTag as e:
        raise CryptoError(f"bloco {counter} inválido (chave errada?)") from e
