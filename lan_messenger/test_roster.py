"""Teste da janela principal: agrupamento, presença e perfil. Roda: python -m lan_messenger.test_roster"""
from __future__ import annotations

import tempfile

from . import profile, roster


def main() -> None:
    peers = {
        "10.0.0.2": {"display": "Eder Silva TI", "dept": "General", "status": "online"},
        "10.0.0.3": {"display": "Karol", "dept": "Almoxarifado", "status": "online"},
        "10.0.0.4": {"display": "Fabricio", "dept": "Almoxarifado", "status": "offline"},
        "10.0.0.5": {"name": "sem-dept", "status": "online"},  # beacon antigo
    }
    g = roster.group_peers(peers)
    assert list(g) == ["Almoxarifado", "Geral"], list(g)
    assert [roster.label_of(i) for _, i in g["Almoxarifado"]] == ["Fabricio", "Karol"]
    assert [roster.label_of(i) for _, i in g["Geral"]] == ["Eder Silva TI", "sem-dept"]
    g2 = roster.group_peers(peers, hide_offline=True)
    assert len(g2["Almoxarifado"]) == 1  # Fabricio oculto
    print("OK group_peers (ordem + Geral padrão + legado General + hide_offline)")

    tmp = tempfile.mkdtemp()
    p, s = profile.load(base=tmp)
    assert p.department == "Geral" and s.away_after_min == 10
    p.display_name = "Eder Silva TI Matriz #Ramal 219"
    p.department = "TI"
    s.hide_offline = True
    profile.save(p, s, base=tmp)
    p2, s2 = profile.load(base=tmp)
    assert p2.display_name.startswith("Eder") and p2.department == "TI"
    assert s2.hide_offline is True and p2.effective_display() == p.display_name
    print("OK profile load/save (Meus Dados + Geral)")
    print("TESTE ROSTER: PASSOU")


if __name__ == "__main__":
    main()
