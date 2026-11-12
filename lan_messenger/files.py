"""Transferência de arquivos P2P via TCP (header JSON + bytes raw)."""
from __future__ import annotations

import hashlib
import os
import socket
import threading
from typing import Callable  # typing p/ rodar no 3.8 (abc só vale em anotação)
from pathlib import Path

from . import config, crypto, protocol

OnFile = Callable[[dict, Path, str], None]  # (header, saved_path, sender_ip)
OnRequest = Callable[[dict], bool]  # (header) -> aceitar? (modo "perguntar")
OnProgress = Callable[[str, int, int], None]  # (filename, done, total)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_sender_dir(name: str) -> str:
    """Pasta por remetente em inbox/: só caracteres seguros no Windows."""
    clean = "".join(c for c in (name or "").strip() if c not in '<>:"/\\|?*')
    clean = " ".join(clean.split()).strip().strip(".")[:60]
    return clean or "Desconhecido"


class FileServer:
    def __init__(self, inbox: Path | str | None = None,
                 on_file: OnFile | None = None,
                 tcp_port: int | None = None,
                 on_request: OnRequest | None = None,
                 key: bytes | None = None):
        self.inbox = Path(inbox) if inbox else config.APP_DATA / "inbox"
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.on_file = on_file or (lambda h, p: None)
        # hook do modo "Pergunte pela primeira permissão": recebe o header
        # APÓS bytes+sha ok e decide antes do ACK (False = apaga + recusa).
        self.on_request = on_request
        self.key = key  # PSK AES-GCM p/ blocos; mutável p/ troca em runtime
        self.tcp_port = tcp_port or config.TCP_FILE_PORT
        self._stop = threading.Event()
        self._sock: socket.socket | None = None

    def set_inbox(self, inbox: Path | str) -> None:
        self.inbox = Path(inbox)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def start(self) -> "FileServer":
        self._stop.clear()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.tcp_port))
        self._sock.listen(10)
        self._sock.settimeout(1.0)
        threading.Thread(target=self._serve, daemon=True, name="file-server").start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _serve(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn, addr[0]),
                             daemon=True).start()

    def _handle(self, conn: socket.socket, ip: str) -> None:
        with conn:
            try:
                header = protocol.recv_frame(conn)
            except (ConnectionError, ValueError, OSError):
                return
            if header.get("type") != "file-header":
                return
            filename = Path(str(header.get("filename", "arquivo.bin"))).name
            size = int(header.get("size", 0) or 0)
            expected = str(header.get("sha256", ""))
            file_id = str(header.get("id", ""))
            want_enc = bool(header.get("enc"))
            if want_enc and self.key is None:
                try:
                    protocol.send_frame(conn, protocol.make_file_ack(
                        file_id, False, "remetente usa criptografia: configure a mesma chave (Rede)"))
                except OSError:
                    pass
                return
            enc = want_enc and self.key is not None
            folder = self.inbox / safe_sender_dir(str(header.get("from_name", "")))
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / filename
            # evita sobrescrever: arquivo (1).ext
            i = 1
            while dest.exists():
                dest = folder / f"{dest.stem} ({i}){dest.suffix}"
                i += 1
            try:
                conn.settimeout(30.0)
                h = hashlib.sha256()
                remaining = size
                counter = 0
                with open(dest, "wb") as f:
                    while remaining > 0:
                        take = min(config.CHUNK_SIZE, remaining)
                        wire = take + (crypto.TAG_LEN if enc else 0)
                        chunk = b""
                        while len(chunk) < wire:
                            part = conn.recv(wire - len(chunk))
                            if not part:
                                raise ConnectionError("transferência interrompida")
                            chunk += part
                        if enc:
                            assert self.key is not None
                            try:
                                chunk = crypto.open_chunk(self.key, file_id, counter, chunk)
                            except crypto.CryptoError as e:
                                raise ConnectionError(str(e)) from e
                            counter += 1
                        f.write(chunk)
                        h.update(chunk)
                        remaining -= take
                ok = (h.hexdigest() == expected) if expected else True
                err = "" if ok else "sha256 divergente"
                if ok and self.on_request is not None:
                    try:
                        allowed = self.on_request(header)
                    except Exception:
                        allowed = True  # falha no hook não pode travar recebimento
                    if not allowed:
                        ok = False
                        err = "recusado pelo usuário"
                if not ok:
                    dest.unlink(missing_ok=True)
                else:
                    try:
                        self.on_file(header, dest, ip)
                    except Exception:
                        pass
                try:
                    protocol.send_frame(conn, protocol.make_file_ack(
                        str(header.get("id", "")), ok, err))
                except OSError:
                    pass
            except (OSError, ConnectionError, ValueError) as e:
                try:
                    protocol.send_frame(conn, protocol.make_file_ack(
                        str(header.get("id", "")), False, str(e)))
                except OSError:
                    pass
                try:
                    dest.unlink(missing_ok=True)
                except OSError:
                    pass


def send_file(ip: str, path: str | Path, from_name: str = "",
              tcp_port: int | None = None,
              on_progress: OnProgress | None = None,
              timeout: float = 120.0, key: bytes | None = None) -> str:
    """Envia um arquivo. Retorna o id. Levanta exceção se falhar.

    timeout alto (120s): o destino no modo 'perguntar' segura o ACK até
    o usuário aceitar/recusar.
    """
    port = tcp_port or config.TCP_FILE_PORT
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    size = p.stat().st_size
    digest = sha256_of(p)
    header = protocol.make_file_header(from_name or config.my_hostname(),
                                       p.name, size, digest)
    header["enc"] = key is not None
    with socket.create_connection((ip, port), timeout=config.ACK_TIMEOUT) as sock:
        protocol.send_frame(sock, header)
        sent = 0
        counter = 0
        with open(p, "rb") as f:
            while True:
                plain = f.read(config.CHUNK_SIZE)
                if not plain:
                    break
                chunk = crypto.seal_chunk(key, header["id"], counter, plain) \
                    if key is not None else plain
                if key is not None:
                    counter += 1
                sock.sendall(chunk)
                sent += len(plain)
                if on_progress:
                    # retornar False cancela (GUI usa p/ botão Cancelar)
                    if on_progress(p.name, sent, size) is False:
                        raise ConnectionError("cancelado pelo usuário")
        ack = protocol.recv_frame(sock, timeout=timeout)
        if ack.get("type") != "file-ack" or not ack.get("ok"):
            raise ConnectionError(f"peer recusou/falhou: {ack.get('error', ack)}")
    return header["id"]
