"""Teste de transferência com aceite/recusa + log em arquivo. Roda: python -m lan_messenger.test_transfer_log"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from . import files, logger, profile


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    # 1. settings: compat com formato antigo + novos campos
    p, s = profile.load(base=tmp)
    assert s.file_accept == "auto" and s.log_mode == "single"
    (tmp / "settings.json").write_text('{"auto_download_files": false}', encoding="utf-8")
    _, s2 = profile.load(base=tmp)
    assert s2.file_accept == "ask", s2.file_accept
    s2.log_mode = "per_user"
    s2.log_dir = str(tmp / "logs")
    s2.approved_senders.append("PC-A")
    profile.save(p, s2, base=tmp)
    _, s3 = profile.load(base=tmp)
    assert s3.approved_senders == ["PC-A"] and s3.log_mode == "per_user"
    print("OK settings (compat auto_download_files + ask + approved)")

    # 2. logger single + per_user
    s3.log_enabled = True
    s3.log_mode = "single"
    dest = logger.log_message(s3, "Eder", "in", "bom dia")
    assert dest and dest.is_file() and "bom dia" in dest.read_text(encoding="utf-8")
    s3.log_mode = "per_user"
    s3.log_user_subdir = True
    dest2 = logger.log_message(s3, "Eder Silva TI", "out", "opa")
    assert dest2 and "Eder_Silva_TI" in str(dest2) and "opa" in dest2.read_text(encoding="utf-8")
    s3.log_enabled = False
    assert logger.log_message(s3, "Eder", "in", "x") is None
    print(f"OK logger (single={dest.name}, per_user={dest2.parent.name}/...)")

    # 3. FileServer recusa (modo perguntar) apaga + sender recebe erro
    inbox = tmp / "inbox"
    srv = files.FileServer(inbox=inbox, on_request=lambda h: False,
                           tcp_port=50301).start()
    src = tmp / "doc.txt"
    src.write_text("conteudo" * 100, encoding="utf-8")
    try:
        files.send_file("127.0.0.1", src, from_name="PC-A", tcp_port=50301)
        raise AssertionError("deveria recusar")
    except ConnectionError as e:
        assert "recusado" in str(e), e
    time.sleep(0.2)
    assert [p for p in inbox.rglob("*") if p.is_file()] == [], list(inbox.rglob("*"))
    print("OK file recusado (apagado + erro 'recusado pelo usuário')")

    # 4. FileServer aceita
    srv.stop()
    srv2 = files.FileServer(inbox=inbox, on_request=lambda h: True,
                            tcp_port=50302).start()
    files.send_file("127.0.0.1", src, from_name="PC-A", tcp_port=50302)
    time.sleep(0.3)
    got = list((inbox / "PC-A").glob("*"))
    assert got and got[0].read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    srv2.stop()
    print("OK file aceito (pasta do remetente)")
    # nome hostil não escapa da inbox (anti path traversal)
    assert files.safe_sender_dir('..\\..\\x') == 'x'
    assert files.safe_sender_dir('a<b:c"D/e\\f|g?h*i') == 'abcDefghi'
    assert files.safe_sender_dir('') == 'Desconhecido'
    print("OK safe_sender_dir")
    print("TESTE TRANSFER LOG: PASSOU")


if __name__ == "__main__":
    main()
