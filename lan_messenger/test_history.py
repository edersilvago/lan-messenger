"""Teste do histórico com busca + lista de peers. Roda: python -m lan_messenger.test_history"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .store import Store


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "h.db"
    s = Store(db)
    s.add_message("1", "10.0.0.2", "in", "bom dia")
    s.add_message("2", "10.0.0.2", "out", "bom dia, Eder")
    s.add_message("3", "192.168.30.5", "in", "preciso do romaneio")
    assert s.list_peers() == ["10.0.0.2", "192.168.30.5"], s.list_peers()
    w = s.messages_with("10.0.0.2")
    assert len(w) == 2 and w[0][1] == "bom dia", w
    r = s.search_messages("romaneio")
    assert len(r) == 1 and r[0][0] == "192.168.30.5", r
    r2 = s.search_messages("BOM DIA")  # LIKE é case-insensitive p/ ASCII
    assert len(r2) == 2, r2
    assert s.search_messages("zzz-nada") == []
    print("OK list_peers + messages_with + search_messages")
    print("TESTE HISTORY: PASSOU")


if __name__ == "__main__":
    main()
