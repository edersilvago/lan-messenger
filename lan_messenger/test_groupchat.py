"""Teste do lote 1.3: ordem de grupos, Geral padrão, cancelamento. Roda: python -m lan_messenger.test_groupchat"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from . import files, roster


def main() -> None:
    # 1. grupo padrão Geral (sem dept)
    g = roster.group_peers({"9.9.9.9": {}})
    assert list(g) == ["Geral"], list(g)
    print("OK grupo padrão Geral")

    # 2. ordem manual
    labels = ["TI", "RH", "Geral"]
    assert roster.order_labels(labels, []) == ["Geral", "RH", "TI"]
    assert roster.order_labels(labels, ["RH", "TI"]) == ["RH", "TI", "Geral"]
    assert roster.order_labels(labels, ["TI", "TI", "RH"]) == ["TI", "RH", "Geral"]
    print("OK order_labels (manual + resto alfabético)")

    # 3. cancelamento no primeiro bloco
    tmp = Path(tempfile.mkdtemp())
    srv = files.FileServer(inbox=tmp / "inbox", tcp_port=50411).start()
    src = tmp / "grande.bin"
    src.write_bytes(b"x" * (3 * 64 * 1024))
    calls: list = []

    def prog(name, done, total):
        calls.append((done, total))
        return False  # cancela de imediato
    try:
        files.send_file("127.0.0.1", src, from_name="A", tcp_port=50411,
                        on_progress=prog)
        raise AssertionError("deveria cancelar")
    except ConnectionError as e:
        assert "cancelado" in str(e), e
    assert calls, "progress deveria ter sido chamado"
    srv.stop()
    print("OK cancelamento via on_progress=False")

    # 4. progresso normal relata 100%
    srv2 = files.FileServer(inbox=tmp / "inbox2", tcp_port=50412).start()
    seen: list = []
    files.send_file("127.0.0.1", src, from_name="A", tcp_port=50412,
                    on_progress=lambda n, d, t: seen.append((d, t)))
    assert seen and seen[-1][0] == seen[-1][1] == src.stat().st_size, seen[-1:]
    srv2.stop()
    time.sleep(0.2)
    print("OK progresso até 100%")
    print("TESTE GROUPCHAT: PASSOU")


if __name__ == "__main__":
    main()
