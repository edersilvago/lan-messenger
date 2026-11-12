"""Teste da 1.5: auto-detecção de IDs, _conf_value, link Abrir pasta.
Roda: python -m lan_messenger.test_detect
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from . import remote


def main() -> None:
    # 1. _conf_value lê 'chave=valor' (AnyDesk) e "chave = 'valor'" (TOML)
    tmp = Path(tempfile.mkdtemp())
    conf = tmp / "service.conf"
    conf.write_text("ad.anynet.id=123456789\nother=x\n", encoding="utf-8")
    assert remote._conf_value(str(conf), "ad.anynet.id") == "123456789"
    toml = tmp / "RustDesk.toml"
    toml.write_text("id = '334872392'\nrendezvous_server = 'x'\n", encoding="utf-8")
    assert remote._conf_value(str(toml), "id") == "334872392"
    assert remote._conf_value(str(tmp / "nao-existe"), "id") == ""
    assert remote._conf_value(str(conf), "ausente") == ""
    print("OK _conf_value (chave=valor + TOML + ausente)")

    # 2. _digits_only
    assert remote._digits_only("AnyDesk ID: 12 345\n") == "12345"
    assert remote._digits_only("") == ""
    print("OK _digits_only")

    # 3. detecção real nesta máquina (ambos instalados aqui)
    ad = remote.get_anydesk_id()
    rd = remote.get_rustdesk_id()
    print(f"   AnyDesk={ad or '(sem)'} RustDesk={rd or '(sem)'}")
    # se existir, precisa ser numérico e com tamanho plausível
    assert ad == "" or (ad.isdigit() and 9 <= len(ad) <= 11), ad
    assert rd == "" or (rd.isdigit() and 6 <= len(rd) <= 12), rd
    print("OK get_anydesk_id / get_rustdesk_id (formato)")

    # 4. com exe inexistente não explode (retorna '')
    assert remote.get_anydesk_id(exe=str(tmp / "nao.exe")) == "" or ad != ""
    assert remote.get_rustdesk_id(exe=str(tmp / "nao.exe")) == "" or rd != ""
    print("OK fallback sem exe")

    # 5. IDs sobrevivem ao save/load do perfil (beacon usa isso)
    from . import profile
    base = tempfile.mkdtemp()
    p, s = profile.load(base=base)
    p.anydesk_id, p.rustdesk_id = ad or "1", rd or "2"
    profile.save(p, s, base=base)
    p2, _ = profile.load(base=base)
    assert (p2.anydesk_id, p2.rustdesk_id) == (p.anydesk_id, p.rustdesk_id)
    print("OK IDs no perfil")
    print("TESTE DETECT: PASSOU")


if __name__ == "__main__":
    main()
