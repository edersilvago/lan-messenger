"""Chat P2P via TCP direto (1-1 + broadcast por fan-out)."""
from __future__ import annotations

import socket
import threading
from typing import Callable  # typing p/ rodar no 3.8 (abc só vale em anotação)

from . import config, crypto, protocol

OnMessage = Callable[[dict, str], None]  # (msg, sender_ip)
OnHello = Callable[[], dict]  # retorna o beacon local (resposta ao hello TCP)


class ChatServer:
    def __init__(self, on_message: OnMessage | None = None,
                 tcp_port: int | None = None,
                 key: bytes | None = None,
                 on_hello: OnHello | None = None):
        self.on_message = on_message or (lambda msg, ip: None)
        self.tcp_port = tcp_port or config.TCP_CHAT_PORT
        self.key = key  # PSK AES-GCM; mutável p/ troca em runtime
        self.on_hello = on_hello
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> "ChatServer":
        self._stop.clear()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.tcp_port))
        self._sock.listen(20)
        self._sock.settimeout(1.0)
        self._thread = threading.Thread(target=self._serve, daemon=True, name="chat-server")
        self._thread.start()
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
                msg = crypto.recv_obj(conn, self.key)
            except (ConnectionError, ValueError, OSError, crypto.CryptoError):
                return
            kind = msg.get("type")
            if kind == "hello":
                # presença via TCP: responde o beacon sem abrir conversa
                try:
                    beacon = self.on_hello() if self.on_hello else {}
                    crypto.send_obj(conn, beacon, self.key)
                except OSError:
                    pass
                return
            if kind != "msg":
                return
            try:
                self.on_message(msg, ip)
            finally:
                try:
                    crypto.send_obj(conn, protocol.make_ack(str(msg.get("id", ""))),
                                    self.key)
                except OSError:
                    pass


def send_message(ip: str, text: str, from_name: str = "", from_user: str = "",
                 tcp_port: int | None = None,
                 timeout: float | None = None, bcast: bool = False,
                 key: bytes | None = None) -> str:
    """Envia texto p/ um peer. Retorna o id. Levanta OSError/TimeoutError se falhar."""
    port = tcp_port or config.TCP_CHAT_PORT
    timeout = timeout or config.ACK_TIMEOUT
    msg = protocol.make_msg(from_name or config.my_hostname(),
                            from_user or config.my_user(), text, to=ip, bcast=bcast)
    with socket.create_connection((ip, port), timeout=timeout) as sock:
        crypto.send_obj(sock, msg, key, timeout=timeout)
        ack = crypto.recv_obj(sock, key, timeout=timeout)
        if ack.get("type") != "ack" or ack.get("id") != msg["id"]:
            raise ConnectionError(f"ACK inválido de {ip}: {ack}")
    return msg["id"]


def fetch_presence(ip: str, from_name: str = "", from_user: str = "",
                   tcp_port: int | None = None,
                   timeout: float = 3.0,
                   key: bytes | None = None) -> dict:
    """Pede o beacon do peer via TCP (fallback quando o UDP falha na VPN).

    Retorna o beacon. Levanta OSError/TimeoutError/ConnectionError se falhar.
    """
    port = tcp_port or config.TCP_CHAT_PORT
    hello = protocol.make_hello(from_name or config.my_hostname(),
                                from_user or config.my_user())
    with socket.create_connection((ip, port), timeout=timeout) as sock:
        crypto.send_obj(sock, hello, key, timeout=timeout)
        reply = crypto.recv_obj(sock, key, timeout=timeout)
        if not isinstance(reply, dict) or reply.get("type") != "beacon":
            raise ConnectionError(f"resposta de presença inválida de {ip}")
        return reply


def send_broadcast(peers: list[str], text: str, **kw) -> dict[str, str]:
    """Fan-out: tenta enviar p/ cada IP. Retorna {ip: 'ok' | 'erro: ...'}."""
    result: dict[str, str] = {}
    for ip in peers:
        try:
            send_message(ip, text, **{**kw, "bcast": True})
            result[ip] = "ok"
        except Exception as e:  # noqa: BLE001 - MVP: reporta por peer
            result[ip] = f"erro: {e}"
    return result
