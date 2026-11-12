"""Teste da trava de instância única. Roda: python -m lan_messenger.test_single_instance"""
from __future__ import annotations

from . import single_instance


def main() -> None:
    a = single_instance.acquire()
    assert a is not None, "primeira trava deveria conseguir"
    b = single_instance.acquire()
    assert b is None, "segunda trava deveria falhar"
    single_instance.release(a)
    c = single_instance.acquire()
    assert c is not None, "após liberar deveria conseguir de novo"
    single_instance.release(c)
    print("OK acquire/release/exclusividade")
    print("TESTE SINGLE INSTANCE: PASSOU")


if __name__ == "__main__":
    main()
