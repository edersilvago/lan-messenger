"""Teste das faixas VPN (expansão + discovery unicast). Roda: python -m lan_messenger.test_vpn_ranges"""
from __future__ import annotations

import tempfile
import time

from . import discovery, networks


def main() -> None:
    # 1. expansão
    assert networks.expand_range("10.0.0.1-10.0.0.3") == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
    assert networks.expand_range("10.0.0.5") == ["10.0.0.5"]
    assert networks.directed_broadcast("192.168.30.1-192.168.30.254") == "192.168.30.255"
    try:
        networks.expand_range("10.0.0.1-10.1.0.0")  # ~65k IPs
        raise AssertionError("deveria barrar faixa gigante")
    except ValueError:
        pass
    print("OK networks.expand/parse/limite")

    # 2. discovery unicast 127.0.0.1 (simula túnel VPN no mesmo PC)
    # Nota: no Windows 2 sockets não dividem a mesma porta UDP, por isso
    # cada instância escuta numa porta e envia na porta da outra.
    f1 = tempfile.mktemp(suffix="_net1.json")
    f2 = tempfile.mktemp(suffix="_net2.json")
    a = discovery.Discovery(name="PC-A", user="a", udp_port=50201, send_port=50202,
                            broadcast="127.0.0.1",
                            ranges=["127.0.0.1-127.0.0.1"],
                            networks_file=f1).start()
    b = discovery.Discovery(name="PC-B", user="b", udp_port=50202, send_port=50201,
                            broadcast="127.0.0.1",
                            ranges=["127.0.0.1-127.0.0.1"],
                            networks_file=f2).start()
    time.sleep(6.5)  # 1-2 beacons
    pa, pb = a.get_peers(), b.get_peers()
    assert any(v.get("name") == "PC-B" for v in pa.values()), f"A nao viu B: {pa}"
    assert any(v.get("name") == "PC-A" for v in pb.values()), f"B nao viu A: {pb}"
    print(f"OK discovery via unicast (A vê {len(pa)}, B vê {len(pb)})")

    # 3. persistência add/del
    n = a.add_range("192.168.30.1-192.168.30.5")
    assert n == 5 and "192.168.30.1-192.168.30.5" in a.get_ranges()
    assert a.del_range("192.168.30.1-192.168.30.5")
    print("OK add/del_range + networks.json")
    a.stop(); b.stop()
    print("TESTE VPN RANGES: PASSOU")


if __name__ == "__main__":
    main()
