"""Teste da tela Mensagens + grupos. Roda: python -m lan_messenger.test_message_prefs"""
from __future__ import annotations

import tempfile

from . import chatview, profile, roster


def main() -> None:
    # 1. fontes e linhas
    assert chatview.font_px("normal") == 9
    assert chatview.font_px("large") == 11
    assert chatview.font_px("xlarge") == 13
    assert chatview.font_px("ork") == 11
    assert chatview.format_line("in", "Ana", "oi", "01/01 - 10:00", True) == \
        "[01/01 - 10:00] Ana: oi"
    assert chatview.format_line("in", "Ana", "oi", "01/01 - 10:00", False) == "Ana: oi"
    assert chatview.format_line("out", "eu", "opa", "", True) == "eu: opa"
    assert chatview.invite_text("Eder").startswith("[Convite]")
    print("OK chatview (fontes, linhas, convite)")

    # 2. aliases + ocultar
    peers = {
        "1": {"display": "A", "dept": "TI", "status": "online"},
        "2": {"display": "B", "dept": "RH", "status": "online"},
    }
    g = roster.group_peers(peers, aliases={"TI": "Tecnologia"}, hidden=["RH"])
    assert list(g) == ["Tecnologia"], list(g)
    g2 = roster.group_peers(peers)
    assert list(g2) == ["RH", "TI"]
    print("OK group_peers (alias + hidden)")

    # 3. persistência das prefs
    tmp = tempfile.mkdtemp()
    p, s = profile.load(base=tmp)
    assert s.show_recent and s.show_datetime and s.incoming_behavior == "foreground"
    assert s.font_size == "large" and not s.keep_focus
    s.show_datetime = False
    s.incoming_behavior = "minimize"
    s.keep_focus = True
    s.font_size = "xlarge"
    s.group_aliases = {"TI": "Tecnologia"}
    s.hidden_groups = ["RH"]
    profile.save(p, s, base=tmp)
    _, s2 = profile.load(base=tmp)
    assert s2.show_datetime is False and s2.incoming_behavior == "minimize"
    assert s2.keep_focus and s2.font_size == "xlarge"
    assert s2.group_aliases == {"TI": "Tecnologia"} and s2.hidden_groups == ["RH"]
    print("OK prefs Mensagens + Grupos (save/load)")
    print("TESTE MESSAGE PREFS: PASSOU")


if __name__ == "__main__":
    main()
