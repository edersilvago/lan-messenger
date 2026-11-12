"""Teste da 1.4: remoto, geometria, IDs no beacon. Roda: python -m lan_messenger.test_remote"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from . import chatview, discovery, profile, protocol, remote


def main() -> None:
    # 1. IP válido/inválido + anti-injeção
    assert remote.valid_ip("192.168.30.20")
    assert remote.valid_ip(" 10.0.0.1 ")
    assert not remote.valid_ip("999.1.1.1")
    assert not remote.valid_ip("10.0.0.1 && calc")
    assert not remote.valid_ip("")
    try:
        remote.open_cmd_ping("10.0.0.1 && calc")
        raise AssertionError("injeção deveria ser barrada")
    except ValueError:
        pass
    print("OK valid_ip + anti-injeção")

    # 2. IDs: limpeza + comandos (sem lançar apps reais)
    assert remote.clean_id(" 12 3456 789 ") == "12 3456 789"
    try:
        remote.connect_anydesk("", exe="inexistente")
        raise AssertionError("id vazio deveria falhar")
    except ValueError:
        pass
    dummy = tempfile.mktemp(suffix=".exe")
    Path(dummy).write_text("nao-executavel", encoding="utf-8")
    try:
        remote.connect_anydesk("123", exe=dummy)
        raise AssertionError("exe inválido deveria falhar no Popen")
    except OSError:
        pass
    try:
        remote.connect_rustdesk("123", exe=dummy)
        raise AssertionError("exe inválido deveria falhar no Popen")
    except OSError:
        pass
    Path(dummy).unlink(missing_ok=True)
    print("OK validação de IDs/exe (Popen com dummy falha limpo)")

    # 3. beacon carrega os IDs; descoberta guarda
    b = protocol.make_beacon("PC", "u", anydesk="111", rustdesk="222 333")
    assert b["anydesk"] == "111" and b["rustdesk"] == "222 333", b
    import json as _j
    d = discovery.Discovery(name="X", user="x", udp_port=50998, ranges=[],
                            networks_file=":mem-r:")
    d._on_datagram(_j.dumps(b).encode("utf-8"), "10.9.9.9")
    info = d.get_peers()["10.9.9.9"]
    assert info["anydesk"] == "111" and info["rustdesk"] == "222 333", info
    # peer antigo (sem campos): vira "" em vez de quebrar
    d._on_datagram(b'{"type":"beacon","name":"V","user":"v"}', "10.9.9.8")
    info2 = d.get_peers()["10.9.9.8"]
    assert info2["anydesk"] == "" and info2["rustdesk"] == ""
    print("OK IDs no beacon/discovery (com + sem compat)")

    # 4. geometria válida/inválida + persistência
    assert chatview.valid_geometry("480x420")
    assert chatview.valid_geometry("300x620+10+10")
    assert not chatview.valid_geometry("banana")
    assert not chatview.valid_geometry("480x420+10")  # incompleto
    assert not chatview.valid_geometry("")
    tmp = tempfile.mkdtemp()
    p, s = profile.load(base=tmp)
    assert s.main_geometry == "" and s.chat_geometry == "650x620"
    assert p.anydesk_id == "" and p.rustdesk_id == ""
    p.anydesk_id = "123456"
    s.main_geometry = "300x620+5+5"
    profile.save(p, s, base=tmp)
    p2, s2 = profile.load(base=tmp)
    assert p2.anydesk_id == "123456" and s2.main_geometry == "300x620+5+5"
    print("OK geometria + IDs (save/load)")
    print("TESTE REMOTE: PASSOU")


if __name__ == "__main__":
    main()
