"""Teste da v1.26: menções @nome, toast (fallback) e link do projeto.

Roda: python -m lan_messenger.test_mentions
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from . import config
from . import toaster
from . import profile as profile_mod
from .app_gui import GITHUB_URL, HELP_TEXT, mentioned_me


def main() -> None:
    # 1. detecção de menções (sem acento/caixa, nome de exibição ou usuário)
    assert mentioned_me("oi @Eder Silva, olha isso", "Eder Silva", "eder")
    assert mentioned_me("Oi @EDER SILVA!!", "Eder Silva", "eder")
    assert mentioned_me("@eder confere?", "Eder Silva", "eder")
    assert mentioned_me("aqui @José", "José", "jose")
    assert mentioned_me("chama @jose", "José", "jose")  # sem acento casa
    assert mentioned_me("fala com @eder.parte2 @eder", "eder.parte2", "eder") is True
    # não casa prefixo de nome maior
    assert not mentioned_me("@joaozinho vem cá", "Joao", "joao")
    assert not mentioned_me("@eder.parte2 não sou eu", "eder", "eder")
    assert not mentioned_me("nada aqui", "Eder Silva", "eder")
    assert not mentioned_me("eder@empresa.com não é menção", "eder", "eder")
    assert not mentioned_me("", "Eder Silva", "eder")
    assert not mentioned_me("@eder", "", "")  # sem tokens: nada casa
    print("OK menções (acento/caixa/prefixo/tokens)")

    # 2. toast: fallback sem falha (Win7/sem biblioteca -> False; com -> True)
    sent = toaster.notify("Teste LAN Messenger", "corpo do teste v1.26")
    assert isinstance(sent, bool)
    assert toaster.supports_toast() == sent or sent is False
    print(f"OK toaster (enviado={sent}, disponível={toaster.supports_toast()})")

    # 3. settings: toast_enabled persiste
    tmp = tempfile.mkdtemp()
    p, s = profile_mod.load(tmp)
    assert s.toast_enabled is True  # default
    s.toast_enabled = False
    profile_mod.save(p, s, tmp)
    p2, s2 = profile_mod.load(tmp)
    assert s2.toast_enabled is False
    print("OK settings (toast_enabled persiste)")

    # 4. link do projeto no Ajuda e constante para o Sobre
    assert GITHUB_URL == "https://github.com/edersilvago/lan-messenger"
    assert GITHUB_URL in HELP_TEXT
    assert "9. PROJETO" in HELP_TEXT
    assert config.APP_VERSION == "1.26"
    print("OK ajuda/sobre (link + versão)")
    print("TESTE MENTIONS: PASSOU")


if __name__ == "__main__":
    main()
