"""Teste da 1.14: presença via TCP (hello) + cache de colegas.
Roda: python -m lan_messenger.test_tcp_presence
"""
from __future__ import annotations

import socket
import time

from . import chat, config, discovery


def _free_port() -> int:
    """Porta TCP livre (evita colisão com porta efêmera de outro app)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main() -> None:
    # 1. hello TCP: responde o beacon sem virar mensagem de chat
    port = _free_port()
    got_msg: list = []
    beacon = {"type": "beacon", "name": "PC-B", "user": "b",
              "display": "PC-B", "dept": "Geral", "status": "online",
              "ts": time.time()}
    srv = chat.ChatServer(on_message=lambda m, ip: got_msg.append(m),
                          tcp_port=port,
                          on_hello=lambda: dict(beacon)).start()
    time.sleep(0.3)
    reply = chat.fetch_presence("127.0.0.1", from_name="A", from_user="a",
                                tcp_port=port, timeout=3.0, key=None)
    assert reply.get("type") == "beacon" and reply.get("name") == "PC-B", reply
    assert got_msg == [], got_msg  # hello não abre conversa
    srv.stop()
    print("OK hello TCP (beacon sem mensagem)")

    # 2. note_tcp_beacon registra e limpa o 'sinal fraco'
    d = discovery.Discovery(name="X", user="x", udp_port=50982, ranges=[],
                            networks_file=":mem-tcp:")
    assert d.note_tcp_beacon("10.9.9.9", dict(beacon)) is True
    assert "10.9.9.9" in d.get_peers()
    assert d.is_stale("10.9.9.9") is False
    assert d.note_tcp_beacon("10.9.9.9", {"type": "msg"}) is False
    assert d.note_tcp_beacon("10.9.9.9", "lixo") is False
    print("OK note_tcp_beacon (válido/inválido)")

    # 3. TCP antigo confirma colega que o UDP perdeu (cenário da VPN)
    old = dict(beacon, ts=time.time() - (config.STALE_WARN_AGE + 5))
    with d._lock:
        d._peers["10.9.9.8"] = dict(d._build_info(old, via="udp"))
    assert d.is_stale("10.9.9.8") is True
    assert d.note_tcp_beacon("10.9.9.8", dict(beacon)) is True
    assert d.is_stale("10.9.9.8") is False
    print("OK TCP limpa 'sinal fraco'")

    # 4. cache: salva online, carrega e semeia como offline
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp()) / "peers_cache.json"
    prev = config.PEERS_CACHE_FILE
    config.PEERS_CACHE_FILE = str(tmp)
    try:
        d.save_peer_cache()
        assert tmp.is_file(), "cache deveria existir"
        d2 = discovery.Discovery(name="Y", user="y", udp_port=50983,
                                 ranges=[], networks_file=":mem-tcp2:")
        cache = d2.load_peer_cache()
        assert "10.9.9.9" in cache, sorted(cache)
        d2.seed_known(cache)
        assert "10.9.9.9" not in d2.get_peers()  # não finge online
        info = d2.get_roster()["10.9.9.9"]
        assert info["status"] == "offline" and info["display"] == "PC-B"
        assert d2.peer_age("10.9.9.9") == float("inf")  # "nunca visto"
    finally:
        config.PEERS_CACHE_FILE = prev
    print("OK cache (save/load/seed offline)")

    # 5. local_beacon completo (com a versão do app)
    lb = d.local_beacon()
    assert lb["type"] == "beacon" and lb["name"] == "X", lb
    assert lb["app_version"] == config.APP_VERSION, lb
    assert d.note_tcp_beacon("10.9.9.7", dict(lb, name="Z", user="z")) is True
    assert d.get_peers()["10.9.9.7"]["app_version"] == config.APP_VERSION
    # peer antigo sem o campo: vira "" sem quebrar
    ancient = {"type": "beacon", "name": "W", "user": "w",
               "ts": time.time()}
    assert d.note_tcp_beacon("10.9.9.6", ancient) is True
    assert d.get_peers()["10.9.9.6"]["app_version"] == ""
    print("OK local_beacon + versão do app (com + sem compat)")
    print("TESTE TCP PRESENCE: PASSOU")


if __name__ == "__main__":
    main()
