"""Teste do diagnóstico de descoberta. Roda: python -m lan_messenger.test_diag"""
from __future__ import annotations

import time

from . import chat, discovery, networks


def main() -> None:
    # 1. tcp_ping: porta fechada falha com mensagem; servidor real passa
    ok, msg = networks.tcp_ping("127.0.0.1", 50991, timeout=1.0)
    assert ok is False and msg, (ok, msg)
    srv = chat.ChatServer(tcp_port=50991).start()
    time.sleep(0.3)
    ok, msg = networks.tcp_ping("127.0.0.1", 50991, timeout=2.0)
    assert ok is True, (ok, msg)
    srv.stop()
    print("OK tcp_ping (falha + sucesso)")

    # 2. diag inicial + após beacon
    a = discovery.Discovery(name="D-A", user="a", udp_port=50992, send_port=50993,
                            broadcast="127.0.0.1", ranges=[],
                            networks_file=":mem-diag-a:").start()
    time.sleep(0.5)
    d = a.diag()
    assert d["bind_ok"] is True, d
    assert d["tx_count"] >= 1 and d["last_tx"] > 0, d
    assert d["online"] == 0 and d["last_rx"] == 0
    print(f"OK diag inicial (bind OK, tx={d['tx_count']})")

    b = discovery.Discovery(name="D-B", user="b", udp_port=50993, send_port=50992,
                            broadcast="127.0.0.1", ranges=[],
                            networks_file=":mem-diag-b:").start()
    time.sleep(6.5)
    da, db = a.diag(), b.diag()
    assert da["last_rx"] > 0 and da["last_rx_from"] == "127.0.0.1", da
    assert db["online"] == 1 and db["bind_ok"] is True, db
    print("OK diag após encontro (last_rx + online)")

    # 3. datagrama direto: beacon válido entra, lixo é ignorado
    import json as _j
    d2 = discovery.Discovery(name="X", user="x", udp_port=50995, ranges=[],
                             networks_file=":mem-diag-d:")
    beacon = _j.dumps({"type": "beacon", "name": "Y", "user": "y",
                       "display": "Y", "dept": "TI", "status": "online",
                       "ts": time.time()}).encode("utf-8")
    d2._on_datagram(beacon, "10.9.9.9")
    dd = d2.diag()
    assert dd["online"] == 1 and dd["last_rx_from"] == "10.9.9.9", dd
    assert d2.get_peers()["10.9.9.9"]["dept"] == "TI"
    d2._on_datagram(b"lixo-nao-json", "10.9.9.9")  # ignorado, sem quebrar
    d2._on_datagram(b'{"type":"outro"}', "10.9.9.9")
    assert d2.diag()["online"] == 1
    a.stop(); b.stop()
    print("OK _on_datagram (válido/lixo)")

    # 4. ping: par abrindo é respondido na hora (encontro imediato)
    import socket as _s
    from . import protocol as _proto
    s1 = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
    s1.bind(("127.0.0.1", 50996))
    s1.settimeout(4.0)
    s2 = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
    p = discovery.Discovery(name="P-A", user="pa", udp_port=50997, send_port=50996,
                            broadcast="127.0.0.1", ranges=[],
                            networks_file=":mem-diag-e:")
    ping = _j.dumps(_proto.make_ping("P-B", "pb")).encode("utf-8")
    p._on_datagram(ping, "127.0.0.1", s2)
    data, _ = s1.recvfrom(65535)
    reply = _j.loads(data.decode("utf-8"))
    assert reply.get("type") == "beacon" and reply.get("name") == "P-A", reply
    # ping de si mesmo: sem resposta
    me = _j.dumps(_proto.make_ping("P-A", "pa")).encode("utf-8")
    p._on_datagram(me, "127.0.0.1", s2)
    s1.settimeout(0.5)
    try:
        s1.recvfrom(65535)
        raise AssertionError("não deveria responder ao próprio ping")
    except _s.timeout:
        pass
    s1.close(); s2.close()
    print("OK ping -> beacon imediato (ignora próprio)")
    print("TESTE DIAG: PASSOU")


if __name__ == "__main__":
    main()
