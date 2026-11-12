"""Teste de menus/grupos manuais. Roda: python -m lan_messenger.test_menus"""
from __future__ import annotations

from pathlib import Path

from . import roster


def main() -> None:
    for f in ["arquivos.png", "historico.png", "config.png", "ajuda.png",
              "sobre.png", "user.png", "usergroup.png", "app.ico"]:
        p = Path(__file__).parent / "assets" / f
        assert p.is_file() and p.stat().st_size > 1000, f"asset ausente: {f}"
    print("OK 8 assets")

    peers = {
        "10.0.0.2": {"display": "Karol", "name": "PC-K", "user": "karol", "dept": "Almox", "status": "online"},
        "10.0.0.3": {"display": "Ana", "name": "PC-A", "user": "ana", "dept": "TI", "status": "online"},
    }
    assert roster.peer_key(peers["10.0.0.2"]) == "karol|PC-K"
    # mover usuário p/ outro grupo
    g = roster.group_peers(peers, overrides={"karol|PC-K": "TI"})
    assert sorted(roster.label_of(i) for _, i in g["TI"]) == ["Ana", "Karol"]
    assert "Almox" not in g
    # voltar ao automático
    g2 = roster.group_peers(peers, overrides={})
    assert sorted(g2) == ["Almox", "TI"]
    # grupo novo vazio aparece
    g3 = roster.group_peers(peers, custom=["Comercial"])
    assert "Comercial" in g3 and g3["Comercial"] == []
    # oculto some mesmo vazio
    g4 = roster.group_peers(peers, custom=["Comercial"], hidden=["Comercial"])
    assert "Comercial" not in g4
    print("OK mover usuário + grupo novo + ocultar")
    print("TESTE MENUS: PASSOU")


if __name__ == "__main__":
    main()
