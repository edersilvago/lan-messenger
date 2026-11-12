"""Teste da 1.11: presença estável (goodbye, stale, anti-flicker).
Roda: python -m lan_messenger.test_presence
"""
from __future__ import annotations

import json as _json
import time

from . import config, discovery


def main() -> None:
    # 1. beacon offline move p/ conhecidos (saída graciosa, sem esperar timeout)
    d = discovery.Discovery(name="X", user="x", udp_port=50991, ranges=[],
                            networks_file=":mem-p:")
    on = {"type": "beacon", "name": "Colega", "user": "c", "status": "online",
          "display": "Colega", "dept": "Geral", "ts": time.time()}
    d._on_datagram(_json.dumps(on).encode("utf-8"), "10.9.9.9")
    assert "10.9.9.9" in d.get_peers()
    off = dict(on, status="offline")
    d._on_datagram(_json.dumps(off).encode("utf-8"), "10.9.9.9")
    assert "10.9.9.9" not in d.get_peers()
    assert d.get_roster()["10.9.9.9"]["status"] == "offline"
    print("OK goodbye offline imediato")

    # 2. mark_unreachable após falha de TCP
    d._on_datagram(_json.dumps(on).encode("utf-8"), "10.9.9.9")
    d.mark_unreachable("10.9.9.9")
    assert "10.9.9.9" not in d.get_peers()
    assert d.get_roster()["10.9.9.9"]["status"] == "offline"
    print("OK mark_unreachable")

    # 3. stale: online sem beacon há +20s
    d._on_datagram(_json.dumps(on).encode("utf-8"), "10.9.9.9")
    assert d.is_stale("10.9.9.9") is False
    old = dict(on, ts=time.time() - (config.STALE_WARN_AGE + 5))
    with d._lock:
        d._peers["10.9.9.9"] = dict(d._peers["10.9.9.9"], ts=old["ts"])
    assert d.is_stale("10.9.9.9") is True
    age = d.peer_age("10.9.9.9")
    assert age > config.STALE_WARN_AGE, age
    print("OK stale/sinal fraco")

    # 4. meu próprio beacon (nome+usuário iguais) é ignorado
    me = {"type": "beacon", "name": d.name, "user": d.user,
          "status": "online", "ts": time.time()}
    d._on_datagram(_json.dumps(me).encode("utf-8"), "10.9.9.7")
    assert "10.9.9.7" not in d.get_peers()
    print("OK ignora próprio beacon")

    # 5. timeout maior (60s): não some rápido com jitter da VPN
    assert config.PEER_TIMEOUT >= 60.0, config.PEER_TIMEOUT
    assert config.BEACON_INTERVAL <= 5.0, config.BEACON_INTERVAL
    print("OK timeout 60s + beacon rápido")
    print("TESTE PRESENCE: PASSOU")


if __name__ == "__main__":
    main()
