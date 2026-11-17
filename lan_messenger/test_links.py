"""Teste da v1.27: links clicáveis nos balões (split + abertura).

Roda: python -m lan_messenger.test_links
"""
from __future__ import annotations

import customtkinter as ctk

from lan_messenger import app_gui
from lan_messenger.app_gui import (BUBBLE_LINK_FG, clean_url, open_url,
                                   split_url_segments)


def main() -> None:
    # 1. split puro: sem URL volta texto inteiro num segmento
    assert split_url_segments("bom dia equipe") == [("text", "bom dia equipe")]
    assert split_url_segments("") == [("text", "")]

    # 2. URL sozinha: único segmento url
    assert split_url_segments("https://exemplo.com/a?b=1") == [
        ("url", "https://exemplo.com/a?b=1")]

    # 3. texto + URL + pontuação final fora do link
    assert split_url_segments("olha: https://exemplo.com/x, e veja") == [
        ("text", "olha: "), ("url", "https://exemplo.com/x"), ("text", ", e veja")]
    assert split_url_segments("site www.edersilva.net.") == [
        ("text", "site "), ("url", "www.edersilva.net"), ("text", ".")]

    # 4. pontuação/parêntese final: fica fora do link
    assert clean_url("https://a.com/p(a)gina.") == "https://a.com/p(a)gina"
    assert clean_url("https://a.com/x).") == "https://a.com/x"
    assert clean_url("https://a.com/x,") == "https://a.com/x"
    assert clean_url("https://a.com/x?y=1&z=2.") == "https://a.com/x?y=1&z=2"

    # 5. múltiplas URLs numa mensagem
    segs = split_url_segments("a https://a.com b www.b.com c")
    assert [s[0] for s in segs] == ["text", "url", "text", "url", "text"]
    assert segs[1][1] == "https://a.com" and segs[3][1] == "www.b.com"

    # 6. abertura: www. ganha https://; não levanta exceção
    opened: list[str] = []
    import webbrowser
    real_open = webbrowser.open
    webbrowser.open = lambda u, *a, **k: opened.append(u) or True
    try:
        open_url("www.edersilva.net")
        open_url("https://exemplo.com")
    finally:
        webbrowser.open = real_open
    assert opened == ["https://www.edersilva.net", "https://exemplo.com"], opened
    print("OK split/abertura (segmentos, pontuação, esquema www.)")

    # 7. balão renderiza: sem URL segue 1 label; com URL, link azul clicável
    ctk.set_appearance_mode("Light")
    r = ctk.CTk()
    r.withdraw()
    try:
        host = ctk.CTkScrollableFrame(r, width=500, height=400)
        host.pack()
        plain = app_gui.build_bubble(host, "in", "sem link aqui")
        lbls = [w for w in plain.winfo_children()[0].winfo_children()
                if isinstance(w, ctk.CTkLabel)]
        assert any(w.cget("text") == "sem link aqui" for w in lbls)

        linked = app_gui.build_bubble(
            host, "out", "olha: https://exemplo.com/x, e veja")
        inner = linked.winfo_children()[0]
        url_lbl = [w for w in inner.winfo_children()
                   if isinstance(w, ctk.CTkLabel)
                   and w.cget("text") == "https://exemplo.com/x"]
        assert len(url_lbl) == 1, [w.cget("text") for w in inner.winfo_children()]
        assert str(url_lbl[0].cget("text_color")) == str(BUBBLE_LINK_FG)
        assert int(str(url_lbl[0].cget("cursor")) != "") is not None
        txt_lbls = [w for w in inner.winfo_children()
                    if isinstance(w, ctk.CTkLabel)
                    and "olha" in str(w.cget("text"))]
        assert len(txt_lbls) == 1
        print("OK balão (label único sem link; azul clicável com link)")
    finally:
        try:
            r.destroy()
        except Exception:
            pass
    print("TESTE LINKS: PASSOU")


if __name__ == "__main__":
    main()
