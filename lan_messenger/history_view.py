"""Visualizador do Histórico (tela clássica) em CustomTkinter.

Esquerda: usuários com conversa. Direita: log Incoming/Outgoing com data/hora.
Topo: busca no histórico + Exportar TXT + Fechar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from collections.abc import Callable

import customtkinter as ctk


class HistoryWindow:
    def __init__(self, parent: tk.Misc, store, label_of: Callable[[str], str],
                 select_peer: str = ""):
        self.store = store
        self.label_of = label_of
        self.win = ctk.CTkToplevel(parent)
        self.win.title("Visualizador do Histórico")
        self.win.geometry("900x550")
        self._center(parent)
        self.win.bind("<Escape>", lambda _e: self.win.destroy(), add="+")

        top = ctk.CTkFrame(self.win, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(top, text="Exportar TXT", width=110,
                      command=self.export).pack(side="left")
        ctk.CTkLabel(top, text="Buscar:").pack(side="left", padx=(12, 2))
        self.query = ctk.CTkEntry(top, width=280)
        self.query.pack(side="left")
        self.query.bind("<Return>", lambda e: self.do_search())
        ctk.CTkButton(top, text="Buscar", width=80,
                      command=self.do_search).pack(side="left", padx=2)
        ctk.CTkButton(top, text="Fechar", width=80,
                      command=self.win.destroy).pack(side="right")

        body = ctk.CTkFrame(self.win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=4)
        body.columnconfigure(0, weight=0, minsize=220)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left = ctk.CTkScrollableFrame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.users_box = left
        self.log = ctk.CTkTextbox(right, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        self._peers: list[str] = []
        self._user_btns: dict[str, ctk.CTkButton] = {}
        self.refresh_users()
        if select_peer:
            self.select_peer(select_peer)

    def _center(self, parent: tk.Misc) -> None:
        """Centraliza pela geometria conhecida (900x550)."""
        try:
            w, h = 900, 550
            x = (self.win.winfo_screenwidth() - w) // 2
            y = (self.win.winfo_screenheight() - h) // 2
            self.win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except tk.TclError:
            pass

    def refresh_users(self) -> None:
        self._peers = self.store.list_peers()
        for w in self.users_box.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._user_btns = {}
        for p in self._peers:
            try:
                label = f"{self.label_of(p)}  [{p}]"
            except Exception:
                label = p
            b = ctk.CTkButton(self.users_box, text=label, anchor="w",
                              fg_color="transparent", text_color=("black", "white"),
                              command=lambda peer=p: self.show_peer(peer))
            b.pack(fill="x", pady=1)
            self._user_btns[p] = b

    def select_peer(self, peer: str) -> bool:
        """Pré-seleciona o contato (botão da janela de conversa)."""
        if peer not in self._user_btns:
            return False
        self.show_peer(peer)
        try:
            self.win.title(f"Histórico - {self.label_of(peer)}")
        except Exception:
            pass
        return True

    def _show(self, lines: list[str]) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("end", "\n".join(lines) if lines else "(sem registros)")
        self.log.configure(state="disabled")

    def show_peer(self, peer: str) -> None:
        for p, b in self._user_btns.items():
            try:
                b.configure(fg_color=("gray75", "gray30") if p == peer else "transparent")
            except tk.TclError:
                pass
        rows = self.store.messages_with(peer, limit=500)
        lines = []
        for direction, text, ts in rows:
            tag = "Outgoing" if direction == "out" else "Incoming"
            lines.append(f"{ts} ({tag}):")
            lines.append(text)
        self._show(lines)

    def show_selected(self) -> None:
        for peer in self._peers:
            self.show_peer(peer)
            return

    def do_search(self) -> None:
        q = self.query.get().strip()
        if not q:
            self.show_selected()
            return
        rows = self.store.search_messages(q)
        lines = []
        for peer, direction, text, ts in rows:
            tag = "Outgoing" if direction == "out" else "Incoming"
            try:
                name = self.label_of(peer)
            except Exception:
                name = peer
            lines.append(f"{name} [{peer}]  {ts} ({tag}): {text}")
        self._show(lines)
        self.win.title(f"Histórico - busca '{q}' ({len(rows)})")

    def export(self) -> None:
        content = self.log.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Exportar", "Nada a exportar.", parent=self.win)
            return
        dest = filedialog.asksaveasfilename(
            parent=self.win, defaultextension=".txt",
            filetypes=[("Texto", "*.txt")], initialfile="historico.txt")
        if not dest:
            return
        try:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Exportar", f"Salvo em {dest}", parent=self.win)
        except OSError as e:
            messagebox.showerror("Exportar", str(e), parent=self.win)
