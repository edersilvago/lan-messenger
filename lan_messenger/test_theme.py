"""Teste da 1.18: temas, cores de status e centralização.
Roda: python -m lan_messenger.test_theme
"""
from __future__ import annotations

import tempfile

import customtkinter as ctk

from lan_messenger import app_gui, profile


def main() -> None:
    # 1. tema persiste e normaliza
    tmp = tempfile.mkdtemp()
    _, s = profile.load(base=tmp)
    assert s.theme == "Light", s.theme
    assert profile.Settings(theme="Dark").theme == "Dark"
    assert profile.Settings(theme="banana").theme == "Light"
    s.theme = "Dark"
    p, _ = profile.load(base=tmp)
    profile.save(p, s, base=tmp)
    _, s2 = profile.load(base=tmp)
    assert s2.theme == "Dark", s2.theme
    print("OK tema (default, válido, inválido, save/load)")

    # 2. modos aplicam sem janela
    for mode in ("Light", "Dark", "System"):
        ctk.set_appearance_mode(mode)
    ctk.set_appearance_mode("Light")
    print("OK set_appearance_mode (Light/Dark/System)")

    # 3. paletas por modo existem (balões, lista, status)
    assert app_gui.BUBBLE_IN_BG == ("#FFFFFF", "#1F2C34")
    assert app_gui.BUBBLE_OUT_BG == ("#D9FDD3", "#005C4B")
    assert set(app_gui.ROSTER_STATUS_COLORS) == {"online", "busy", "away", "offline"}
    assert set(app_gui.STATUS_COLORS) == {"online", "busy", "away"}
    print("OK paletas claro/escuro")

    # 4. centralização por geometria conhecida
    ctk.set_appearance_mode("Light")
    r = ctk.CTk()
    r.withdraw()
    try:
        w = ctk.CTkToplevel(r)
        w.geometry("9999x9999")
        app_gui.center_fixed(w, "340x190")
        g = w.geometry()
        ex = (w.winfo_screenwidth() - 340) // 2
        ey = (w.winfo_screenheight() - 190) // 2
        assert g.endswith(f"+{ex}+{ey}"), g
        assert ex > 0, g  # longe da borda esquerda: centralizado
        w.destroy()
        print("OK center_fixed (posição central pela geometria)")
    finally:
        r.destroy()
    print("TESTE THEME: PASSOU")


if __name__ == "__main__":
    main()
