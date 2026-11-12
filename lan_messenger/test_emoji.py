"""Teste da 1.24: emojis (grade + inserção).
Roda: python -m lan_messenger.test_emoji
"""
from __future__ import annotations

import customtkinter as ctk

from lan_messenger import app_gui


def main() -> None:
    assert len(app_gui.EMOJIS) >= 60, len(app_gui.EMOJIS)
    assert "😊" in app_gui.EMOJIS and "👍" in app_gui.EMOJIS
    assert "🎉" in app_gui.EMOJIS and "❤️" in app_gui.EMOJIS
    print(f"OK grade ({len(app_gui.EMOJIS)} emojis)")

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
