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

    # Conversa deve carregar as mensagens mais recentes, em ordem cronológica.
    for i in range(120):
        s.add_message(f"bulk-{i:03}", "10.0.0.9", "in", f"texto {i:03}")
    latest = s.messages_with_ids("10.0.0.9", limit=10)
    assert [row[0] for row in latest] == [
        f"bulk-{i:03}" for i in range(110, 120)
    ], latest
    assert [row[1] for row in s.messages_with("10.0.0.9", limit=3)] == [
        "texto 117", "texto 118", "texto 119"
    ]
    print("OK histórico recente não some após ultrapassar o limite")

    # Reentrega TCP do mesmo id não pode duplicar nem alterar a mensagem.
    assert s.add_message_once("dedup-1", "10.0.0.8", "in", "original") is True
    assert s.add_message_once("dedup-1", "10.0.0.8", "in", "duplicada") is False
    dedup = s.messages_with_ids("10.0.0.8")
    assert len(dedup) == 1 and dedup[0][2] == "original", dedup
    print("OK mensagem recebida é idempotente por id")

    print("TESTE HISTORY: PASSOU")


if __name__ == "__main__":
    main()
