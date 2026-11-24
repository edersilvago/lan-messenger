"""Teste da v1.29: fila de saída (mensagem para contato offline).

Roda: python -m lan_messenger.test_outbox
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from lan_messenger import app_gui, chat, protocol
from lan_messenger.app_gui import bubble_clock, flush_outbox
from lan_messenger.store import Store


def main() -> None:
    # 1. fila no banco: enfileira, lista, conta e remove
    db = Path(tempfile.mkdtemp(prefix="lm_outbox_")) / "h.db"
    s = Store(db)
    s.add_message("m1", "10.0.0.2", "out", "primeira")
    s.queue_message("m1", "10.0.0.2", "primeira")
    s.add_message("m2", "10.0.0.3", "out", "segunda")
    s.queue_message("m2", "10.0.0.3", "segunda")
    assert s.pending_count() == 2
    assert s.pending_count("10.0.0.2") == 1
    assert s.pending_ids("10.0.0.3") == {"m2"}
    pend = s.pending_messages()
    assert [p[0] for p in pend] == ["m1", "m2"], pend
    assert pend[0][1:] == ("10.0.0.2", "primeira")
    print("OK fila no SQLite (queue/list/count/ids)")

    # 2. histórico com id: balão pendente é identificável
    rows = s.messages_with_ids("10.0.0.2")
    assert rows and rows[0][0] == "m1" and rows[0][1] == "out"
    assert s.messages_with("10.0.0.2")[0][:2] == ("out", "primeira")
    print("OK messages_with_ids (id + direcao + texto)")

    # 3. drop remove só o escolhido
    s.drop_pending("m1")
    assert s.pending_ids() == {"m2"}
    print("OK drop_pending")

    # 4. flush: entrega só online, falha não para a fila, remove entregues
    s.queue_message("m1", "10.0.0.2", "primeira")
    s.queue_message("m3", "10.0.0.4", "falha")
    tried: list[tuple[str, str, str]] = []
    delivered: list[tuple[str, str]] = []

    def is_online(ip: str) -> bool:
        return ip != "10.0.0.9"  # 10.0.0.9 nunca tenta

    def send(ip: str, text: str, mid: str) -> None:
        tried.append((ip, text, mid))
        if ip == "10.0.0.4":
            raise OSError("sem rota")

    done = flush_outbox(s, is_online, send,
                        lambda mid, ip, text: delivered.append((mid, ip)))
    assert sorted(done) == ["m1", "m2"], done
    assert ("10.0.0.2", "primeira", "m1") in tried
    assert ("m1", "10.0.0.2") in delivered
    assert s.pending_ids() == {"m3"}, s.pending_ids()
    print("OK flush_outbox (entrega, falha mantida, callback)")

    # 5. contato offline: nem tenta e mantém a fila
    s.queue_message("m4", "10.0.0.9", "offline")
    done2 = flush_outbox(s, is_online, send)
    assert done2 == []
    assert all(mid != "m4" for _ip, _txt, mid in tried), tried
    assert "m4" in s.pending_ids()
    print("OK offline nao tenta (fila preservada)")

    # 6. balão: pendente x entregue
    assert bubble_clock("out", "14/10/2026 - 08:12:33", pending=True) == \
        "08:12:33 (pendente)"
    assert bubble_clock("out", "14/10/2026 - 08:12:33") == "08:12:33 ✓"
    assert bubble_clock("in", "14/10/2026 - 08:12:33", pending=True) == "08:12:33"
    print("OK bubble_clock (pendente / tique)")

    # 7. id estável: protocolo e envio usam o id da fila
    assert protocol.make_msg("A", "a", "oi", msg_id="fixo")["id"] == "fixo"
    assert protocol.make_msg("A", "a", "oi")["id"] != "fixo"

    sent: dict = {}
    real_conn = chat.socket.create_connection
    real_send, real_recv = chat.crypto.send_obj, chat.crypto.recv_obj

    class FakeSock:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_send(sock, obj, key, timeout=10.0):
        sent.clear()
        sent.update(obj)

    def fake_recv(sock, key, timeout=10.0):
        return {"type": "ack", "id": sent["id"]}

    chat.socket.create_connection = lambda *a, **k: FakeSock()
    chat.crypto.send_obj = fake_send
    chat.crypto.recv_obj = fake_recv
    try:
        assert chat.send_message("10.0.0.2", "da fila", msg_id="m1") == "m1"
        assert sent["id"] == "m1" and sent["text"] == "da fila"
        assert chat.send_message("10.0.0.2", "nova") != "m1"
    finally:
        chat.socket.create_connection = real_conn
        chat.crypto.send_obj = real_send
        chat.crypto.recv_obj = real_recv
    print("OK send_message com msg_id estavel")

    # 8. funções da UI existem e estão ligadas ao App
    for name in ("queue_outgoing", "flush_outbox_soon", "_flush_outbox",
                 "_queued_delivered", "_outbox_tick", "_peer_online",
                 "_send_queued"):
        assert callable(getattr(app_gui.App, name)), name
    assert callable(app_gui.flush_outbox)
    print("OK metodos da fila no App")

    # 9. integração real: fila sai por TCP com o id original e limpa o banco
    import socket as _socket
    import time as _time

    sock = _socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    got: list = []
    srv = chat.ChatServer(on_message=lambda m, ip: got.append(m),
                          tcp_port=port).start()
    _time.sleep(0.3)
    try:
        s.queue_message("fila-1", "127.0.0.1", "cheguei depois")
        done3 = flush_outbox(
            s, lambda ip: True,
            lambda ip, text, mid: chat.send_message(
                ip, text, tcp_port=port, msg_id=mid))
        _time.sleep(0.2)
        assert done3 == ["fila-1"], done3
        assert "fila-1" not in s.pending_ids(), s.pending_ids()
        assert got and got[0]["id"] == "fila-1", got
        assert got[0]["text"] == "cheguei depois", got
    finally:
        srv.stop()
    print("OK integracao TCP (fila entregue e removida)")

    print("TESTE OUTBOX: PASSOU")


if __name__ == "__main__":
    main()
