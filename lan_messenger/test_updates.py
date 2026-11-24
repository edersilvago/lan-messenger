"""Teste da v1.37: aviso de nova versão. Roda: python -m lan_messenger.test_updates"""
from __future__ import annotations

import json

from . import updates


class Response:
    def __init__(self, data: dict):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.data).encode("utf-8")


def main() -> None:
    assert updates.version_tuple("v1.37") == (1, 37)
    assert updates.version_tuple("1.37.2") == (1, 37, 2)
    assert updates.version_tuple("lixo") == ()
    assert updates.is_newer("v1.37", "1.36")
    assert not updates.is_newer("v1.36", "1.36")
    assert not updates.is_newer("lixo", "1.36")
    print("OK comparação de versões")

    def newer(_request, timeout=0):
        assert timeout == 4.0
        return Response({
            "tag_name": "v1.38",
            "html_url": "https://github.com/edersilvago/lan-messenger/releases/tag/v1.38",
        })

    got = updates.check_latest("1.37", opener=newer)
    assert got == (
        "1.38",
        "https://github.com/edersilvago/lan-messenger/releases/tag/v1.38",
    ), got

    same = lambda *_a, **_k: Response({
        "tag_name": "v1.37", "html_url": updates.RELEASES_URL})
    assert updates.check_latest("1.37", opener=same) is None

    bad_url = lambda *_a, **_k: Response({
        "tag_name": "v2.0", "html_url": "https://example.com/falso"})
    assert updates.check_latest("1.37", opener=bad_url) == (
        "2.0", updates.RELEASES_URL)

    def broken(*_a, **_k):
        raise OSError("sem internet")

    assert updates.check_latest("1.37", opener=broken) is None
    print("OK consulta, URL segura e falha offline silenciosa")
    print("TESTE UPDATES: PASSOU")


if __name__ == "__main__":
    main()
