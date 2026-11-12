"""Teste da criptografia PSK (chat + arquivos). Roda: python -m lan_messenger.test_crypto"""
from __future__ import annotations

import socket
import tempfile
import time
from pathlib import Path

from . import chat, crypto, files


def main() -> None:
    k1 = crypto.generate_key()
    k2 = crypto.generate_key()
    assert k1 != k2
    key = crypto.parse_key(k1)
    assert key is not None and len(key) == 32
    assert crypto.parse_key("lixo") is None
    assert crypto.parse_key("") is None
    print("OK generate/parse_key")

    # 1. frame selado roundtrip via socketpair
    a, b = socket.socketpair()
    crypto.send_obj(a, {"type": "msg", "text": "segredo"}, key)
    assert crypto.recv_obj(b, key)["text"] == "segredo"
    crypto.send_obj(a, {"type": "msg", "text": "x"}, key)
    try:
        crypto.recv_obj(b, None)
        raise AssertionError("deveria exigir chave")
    except crypto.CryptoError:
        pass
    crypto.send_obj(a, {"type": "msg", "text": "x"}, key)
    try:
        crypto.recv_obj(b, crypto.parse_key(k2))
        raise AssertionError("chave errada deveria falhar")
    except crypto.CryptoError:
        pass
    # claro continua legível com chave configurada (rede mista)
    crypto.send_obj(a, {"type": "msg", "text": "claro"}, None)
    assert crypto.recv_obj(b, key)["text"] == "claro"
    a.close(); b.close()
    print("OK seal/open (roundtrip, sem-chave, chave-errada, misto)")

    # 2. chat criptografado fim a fim
    got: list[dict] = []
    srv = chat.ChatServer(on_message=lambda m, ip: got.append(m),
                          tcp_port=50401, key=key).start()
    time.sleep(0.3)
    mid = chat.send_message("127.0.0.1", "oi cripto", from_name="A", tcp_port=50401, key=key)
    time.sleep(0.5)
    assert got and got[0]["id"] == mid and got[0]["text"] == "oi cripto"
    srv.stop()
    print("OK chat E2E com PSK")

    # 3. arquivo criptografado + chave errada recusa
    tmp = Path(tempfile.mkdtemp())
    inbox = tmp / "inbox"
    fsrv = files.FileServer(inbox=inbox, tcp_port=50402, key=key).start()
    src = tmp / "segredo.txt"
    src.write_text("dados sigilosos " * 5000, encoding="utf-8")  # ~80KB = 2 blocos
    files.send_file("127.0.0.1", src, from_name="A", tcp_port=50402, key=key)
    time.sleep(0.5)
    outs = list(inbox.glob("*"))
    assert outs and outs[0].read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    fsrv.stop()
    print("OK arquivo E2E com PSK (multibloco)")

    fsrv2 = files.FileServer(inbox=tmp / "inbox2", tcp_port=50403,
                             key=crypto.parse_key(k2)).start()
    try:
        files.send_file("127.0.0.1", src, from_name="A", tcp_port=50403, key=key)
        raise AssertionError("chave divergente deveria falhar")
    except ConnectionError:
        pass
    fsrv2.stop()
    print("OK arquivo com chave divergente falha de forma limpa")
    print("TESTE CRYPTO: PASSOU")


if __name__ == "__main__":
    main()
