"""Teste local com 2 instâncias no mesmo PC (portas diferentes + 127.0.0.1).

Roda:  python -m lan_messenger.test_two_instances
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from . import chat, files

CHAT_A, FILE_A = 50101, 50102
CHAT_B, FILE_B = 50111, 50112


def main() -> None:
    inbox_b = Path(tempfile.mkdtemp(prefix="inboxB_"))
    got_msg: list[dict] = []
    got_file: list[Path] = []

    srv_b = chat.ChatServer(on_message=lambda m, ip: got_msg.append(m), tcp_port=CHAT_B).start()
    fsrv_b = files.FileServer(inbox=inbox_b,
                              on_file=lambda h, p, ip="": got_file.append(p),
                              tcp_port=FILE_B).start()
    chat.ChatServer(tcp_port=CHAT_A).start()
    files.FileServer(inbox=tempfile.mkdtemp(prefix="inboxA_"), tcp_port=FILE_A).start()
    time.sleep(0.5)

    # 1. mensagem A -> B
    mid = chat.send_message("127.0.0.1", "ola do A", from_name="PC-A",
                            from_user="a", tcp_port=CHAT_B)
    time.sleep(0.5)
    assert got_msg and got_msg[0]["id"] == mid, f"msg nao chegou: {got_msg}"
    print(f"OK msg: {got_msg[0]['text']!r} id={mid}")

    # 2. arquivo A -> B
    src = Path(tempfile.gettempdir()) / "lan_test_hello.txt"
    src.write_text("conteudo de teste LAN " * 100, encoding="utf-8")
    fid = files.send_file("127.0.0.1", src, from_name="PC-A", tcp_port=FILE_B)
    time.sleep(0.5)
    assert got_file and got_file[0].read_text(encoding="utf-8") == src.read_text(encoding="utf-8"), \
        f"arquivo nao chegou: {got_file}"
    print(f"OK file: id={fid} salvo={got_file[0]} ({got_file[0].stat().st_size} bytes)")

    srv_b.stop(); fsrv_b.stop()
    print("TESTE 2 INSTANCIAS: PASSOU")


if __name__ == "__main__":
    main()
