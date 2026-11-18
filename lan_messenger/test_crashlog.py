"""Teste da v1.28: log de erros em arquivo (logs/crash.log).

Roda: python -m lan_messenger.test_crashlog
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from lan_messenger import app_gui
from lan_messenger.app_gui import log_crash


def main() -> None:
    # 1. caminho padrão: dentro da pasta de dados do app
    assert app_gui.CRASH_LOG.name == "crash.log"
    assert app_gui.CRASH_LOG.parent.name == "logs"
    print("OK caminho padrao:", app_gui.CRASH_LOG)

    tmp = Path(tempfile.mkdtemp(prefix="lm_crash_")) / "sub" / "crash.log"
    real = app_gui.CRASH_LOG
    app_gui.CRASH_LOG = tmp
    try:
        # 2. exceção real: cabeçalho com contexto + traceback completo
        try:
            raise ValueError("falha de teste")
        except ValueError as e:
            path = log_crash("teste_ctx", e)
        assert path == str(tmp)
        text = tmp.read_text(encoding="utf-8")
        assert "[teste_ctx]" in text
        assert "ValueError: falha de teste" in text
        assert "Traceback (most recent call last)" in text
        assert text.rstrip().endswith("ValueError: falha de teste")
        print("OK excecao registrada com contexto e traceback")

        # 3. append: segunda chamada não apaga a primeira
        log_crash("segundo", RuntimeError("outro erro"))
        text2 = tmp.read_text(encoding="utf-8")
        assert text2.count("[teste_ctx]") == 1
        assert "[segundo]" in text2
        assert "RuntimeError: outro erro" in text2
        assert len(text2) > len(text)
        print("OK append (dois registros no mesmo arquivo)")

        # 4. sem exceção: só o cabeçalho, nunca levanta
        log_crash("sem_exc")
        text3 = tmp.read_text(encoding="utf-8")
        assert "[sem_exc]" in text3
        print("OK cabecalho sem excecao")

        # 5. reporter do Tk: grava e avisa na statusbar
        class Root:
            report_callback_exception = None

        class Bar:
            text = ""

            def configure(self, **kw) -> None:
                self.text = str(kw.get("text", ""))

        stub = type("Stub", (), {})()
        stub.root = Root()
        stub.statusbar = Bar()
        app_gui.App._install_crash_reporter(stub)
        assert stub.root.report_callback_exception is not None
        stub.root.report_callback_exception(
            ZeroDivisionError, ZeroDivisionError("div por zero"), None)
        text4 = tmp.read_text(encoding="utf-8")
        assert "[callback Tk]" in text4
        assert "ZeroDivisionError: div por zero" in text4
        assert "Erro interno registrado em" in stub.statusbar.text
        assert str(tmp) in stub.statusbar.text
        print("OK reporter do Tk grava e avisa no rodape")

        # 6. nunca levanta, mesmo com caminho impossível
        app_gui.CRASH_LOG = Path("Z:/nao/existe/crash.log")
        out = log_crash("erro_de_io", RuntimeError("x"))
        assert out == str(app_gui.CRASH_LOG)
        print("OK nao levanta com caminho invalido")
    finally:
        app_gui.CRASH_LOG = real

    print("TESTE CRASHLOG: PASSOU")


if __name__ == "__main__":
    main()
