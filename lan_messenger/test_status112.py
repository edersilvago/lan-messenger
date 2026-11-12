"""Teste da 1.12: status_msg no beacon, mensagens padrão, versículo.
Roda: python -m lan_messenger.test_status112
"""
from __future__ import annotations

import json as _json
import tempfile
import time

from . import app_gui, discovery, profile


def main() -> None:
    # 1. status_msg viaja no beacon e é guardada
    d = discovery.Discovery(name="X", user="x", udp_port=50989, ranges=[],
                            networks_file=":mem-s:")
    d.status_msg = "Ocupado aqui"
    import json as _j
    msg = _j.loads(d._beacon_msg().decode("utf-8"))
    assert msg["status_msg"] == "Ocupado aqui", msg
    d2 = discovery.Discovery(name="Y", user="y", udp_port=50988, ranges=[],
                             networks_file=":mem-s2:")
    d2._on_datagram(_json.dumps(msg).encode("utf-8"), "10.9.9.9")
    assert d2.get_peers()["10.9.9.9"]["status_msg"] == "Ocupado aqui"
    # peer antigo sem o campo: vira "" sem quebrar
    old = {"type": "beacon", "name": "V", "user": "v", "ts": time.time()}
    d2._on_datagram(_json.dumps(old).encode("utf-8"), "10.9.9.8")
    assert d2.get_peers()["10.9.9.8"]["status_msg"] == ""
    print("OK status_msg no beacon (com + sem compat)")

    # 2. mensagens padrão + persistência
    tmp = tempfile.mkdtemp()
    p, s = profile.load(base=tmp)
    assert "ocupado" in s.busy_msg.lower() and "ausente" in s.away_msg.lower()
    s.busy_msg = "Ocupado teste"
    profile.save(p, s, base=tmp)
    _, s2 = profile.load(base=tmp)
    assert s2.busy_msg == "Ocupado teste" and s2.away_msg == s.away_msg
    print("OK mensagens de status (save/load)")

    # 3. ajuda cobre os recursos + Sobre com o versículo
    help_flat = " ".join(app_gui.HELP_TEXT.split())
    for word in ("sinal fraco", "Mensagem de status", "Histórico",
                 "Ocupado", "Ausente", "print"):
        assert word.lower() in help_flat.lower(), word
    import inspect as _insp
    src = _insp.getsource(app_gui.App.about_dialog)
    assert "Mateus 7, 24" in src and "rocha" in src, "versículo no Sobre"
    print("OK ajuda + versículo")
    print("TESTE STATUS112: PASSOU")


if __name__ == "__main__":
    main()
