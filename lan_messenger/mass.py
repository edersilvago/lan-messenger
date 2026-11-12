"""Diálogo Enviar Mensagem em Massa (tela clássica) em CustomTkinter.

Grupos recolhíveis com caixas de seleção + Todos/Nenhum.
Envia via fan-out TCP para os IPs marcados e mostra resultado por peer.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from collections.abc import Callable

import customtkinter as ctk

from . import config, roster


def _icon(name: str, size: int = 16):
    """PNG p/ a árvore (None se Pillow/asset indisponível)."""
    try:
        from PIL import Image
        path = config.asset_path(name)
        if not path:
            return None
        return ctk.CTkImage(Image.open(path).convert("RGBA"), size=(size, size))
    except Exception:  # noqa: BLE001
        return None


def open_mass_dialog(parent: tk.Misc, groups: dict[str, list[tuple[str, dict]]],
                     send_fn: Callable[[list[str], str], dict[str, str]],
                     preselect: list[str] | None = None,
                     title: str = "Enviar Mensagem em Massa") -> None:
    """preselect: nomes de grupo e/ou IPs já marcados (ex msg p/ o grupo)."""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry("860x540")
    win.minsize(760, 460)
    try:
        x = (win.winfo_screenwidth() - 860) // 2
        y = (win.winfo_screenheight() - 540) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
    except tk.TclError:
        pass
    win.bind("<Escape>", lambda _e: win.destroy(), add="+")

    win.columnconfigure(0, weight=1, minsize=440)
    win.columnconfigure(1, weight=0, minsize=280)
    win.rowconfigure(0, weight=1)

    left = ctk.CTkFrame(win, fg_color="transparent")
    left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
    left.columnconfigure(0, weight=1)
    left.rowconfigure(1, weight=1)
    ctk.CTkLabel(left, text="Texto da mensagem:", anchor="w").grid(
        row=0, column=0, sticky="ew")
    txt = ctk.CTkTextbox(left)
    txt.grid(row=1, column=0, sticky="nsew")

    right = ctk.CTkFrame(win, fg_color="transparent")
    right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
    right.columnconfigure(0, weight=1)
    right.rowconfigure(1, weight=1)
    top = ctk.CTkFrame(right, fg_color="transparent")
    top.grid(row=0, column=0, sticky="ew", pady=(0, 4))
    top.columnconfigure(0, weight=1)
    ctk.CTkLabel(top, text="Destinatários:").grid(row=0, column=0, sticky="w")
    sel = tk.StringVar(value="Selecionar")
    box = ctk.CTkScrollableFrame(right)
    box.grid(row=1, column=0, sticky="nsew")
    state: dict[str, bool] = {}        # chave -> marcado
    user_vars: dict[str, tk.BooleanVar] = {}
    group_vars: dict[str, tk.BooleanVar] = {}
    group_users: dict[str, list[str]] = {}  # dept -> [ip...]

    pre = set(preselect or [])
    img_group = _icon("usergroup.png")
    img_user = _icon("user.png")
    win._mass_icons = (img_group, img_user)  # evita GC das imagens

    def paint_all() -> None:
        for dept, var in group_vars.items():
            kids = group_users.get(dept, [])
            var.set(bool(kids) and all(state.get(f"u:{ip}", False) for ip in kids))

    def set_group(dept: str, value: bool) -> None:
        for ip in group_users.get(dept, []):
            state[f"u:{ip}"] = value
            if ip in user_vars:
                user_vars[ip].set(value)
        paint_all()

    def select_all(v: bool) -> None:
        for k in list(state):
            state[k] = v
        for var in list(user_vars.values()) + list(group_vars.values()):
            var.set(v)

    for dept, members in groups.items():
        on = dept in pre
        gvar = tk.BooleanVar(value=on)
        group_vars[dept] = gvar
        group_users[dept] = [ip for ip, _ in members]
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", pady=(4, 0))
        ctk.CTkCheckBox(head, text=f"{dept} ({len(members)})",
                        variable=gvar,
                        command=lambda d=dept, v=gvar: set_group(d, v.get()),
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
        for ip, info in members:
            uon = on or ip in pre
            state[f"u:{ip}"] = uon
            uvar = tk.BooleanVar(value=uon)
            user_vars[ip] = uvar
            mark = roster.STATUS_ICON.get(info.get("status", "online"), "")
            row = ctk.CTkCheckBox(box, text=f"{mark} {roster.label_of(info)}".rstrip(),
                                  variable=uvar,
                                  command=lambda v=uvar, k=f"u:{ip}": (state.__setitem__(k, v.get()), paint_all()))
            row.pack(fill="x", padx=(24, 0))
    paint_all()

    ctk.CTkOptionMenu(top, variable=sel, values=["Selecionar", "Todos", "Nenhum"],
                      command=lambda c: select_all(c == "Todos") if c != "Selecionar" else None,
                      width=130).grid(row=0, column=1, sticky="e")

    bot = ctk.CTkFrame(left, fg_color="transparent")
    bot.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    bot.columnconfigure(0, weight=1)

    def on_send() -> None:
        text = txt.get("1.0", "end").strip()
        ips = [k[2:] for k, on in state.items() if on and k.startswith("u:")]
        if not text:
            messagebox.showinfo("Broadcast", "Digite o texto.", parent=win)
            return
        if not ips:
            messagebox.showinfo("Broadcast", "Marque ao menos um destinatário.", parent=win)
            return
        res = send_fn(ips, text)
        ok = sum(1 for v in res.values() if v == "ok")
        messagebox.showinfo("Broadcast", f"Enviado: {ok}/{len(ips)}\n" +
                            "\n".join(f"{ip}: {st}" for ip, st in res.items()),
                            parent=win)
        win.destroy()

    ctk.CTkButton(bot, text="Cancelar", width=100,
                  command=win.destroy).grid(row=0, column=1, padx=(0, 6))
    ctk.CTkButton(bot, text="Enviar", width=100,
                  command=on_send).grid(row=0, column=2)
