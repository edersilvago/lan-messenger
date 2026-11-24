"""Teste da 1.24/1.39: emojis, atalhos e quebra automática.
Roda: python -m lan_messenger.test_emoji
"""
from __future__ import annotations

import customtkinter as ctk

from lan_messenger import app_gui, chatview


def main() -> None:
    assert len(app_gui.EMOJIS) >= 60, len(app_gui.EMOJIS)
    assert "😊" in app_gui.EMOJIS and "👍" in app_gui.EMOJIS
    assert "🎉" in app_gui.EMOJIS and "❤️" in app_gui.EMOJIS
    print(f"OK grade ({len(app_gui.EMOJIS)} emojis)")

    # v1.39: atalhos de texto viram emoji após envio
    assert chatview.translate_emoticons("oi :)") == "oi 😊"
    assert chatview.translate_emoticons(":(") == "😞"
    assert chatview.translate_emoticons("bom :D") == "bom 😃"
    assert chatview.translate_emoticons(";)") == "😉"
    assert chatview.translate_emoticons(":P") == "😛"
    assert chatview.translate_emoticons("<3") == "❤️"
    assert chatview.translate_emoticons(":O") == "😮"
    assert chatview.translate_emoticons(":/") == "😕"
    assert chatview.translate_emoticons("(y)") == "👍"
    assert chatview.translate_emoticons("(n)") == "👎"
    # não quebra URL
    url = "veja http://a.b/c:/x :)"
    assert chatview.translate_emoticons(url) == "veja http://a.b/c:/x 😊", url
    # sem falso positivo em meio a palavra
    assert chatview.translate_emoticons("file:/x") == "file:/x"
    print("OK atalhos de emoticon")

    # v1.39: quebra automática de palavras longas
    long = "A" * 100
    broken = app_gui.soft_break(long, chunk=30)
    assert "\u200b" in broken
    assert broken.replace("\u200b", "") == long
    short = "oi tudo bem"
    assert app_gui.soft_break(short) == short
    print("OK quebra automática de palavras longas")

    ctk.set_appearance_mode("Light")
    r = ctk.CTk()
    r.withdraw()
    try:
        box = ctk.CTkTextbox(r, height=60)
        box.pack()
        box.insert("1.0", "oi ")
        app_gui._emoji_pick(r, box, "👍")
        assert box.get("1.0", "end").strip() == "oi 👍", repr(box.get("1.0", "end"))
        print("OK inserção no cursor")
    finally:
        r.destroy()
    print("TESTE EMOJI: PASSOU")


if __name__ == "__main__":
    main()
