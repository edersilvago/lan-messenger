"""Teste da v1.30: responder mensagem específica (citação no balão).

Roda: python -m lan_messenger.test_reply
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import customtkinter as ctk

from lan_messenger import app_gui, chat, protocol
from lan_messenger.store import Store


def main() -> None:
    # 1. protocolo: reply só quando pedido, com limites
    m = protocol.make_msg("A", "a", "oi")
    assert "reply" not in m, m
    m2 = protocol.make_msg("A", "a", "oi",
                           reply={"id": "m9", "name": "Ana", "text": "olá"})
    assert m2["reply"] == {"id": "m9", "name": "Ana", "text": "olá"}, m2
    m3 = protocol.make_msg("A", "a", "oi", reply={"id": "x", "name": "N" * 200,
                                                  "text": "T" * 900})
    assert len(m3["reply"]["name"]) == 80
    assert len(m3["reply"]["text"]) == 300
    assert m3["id"] and m3["type"] == "msg"
    print("OK protocolo (reply opcional + limites)")

    # 2. banco: citação ligada à mensagem e por peer
    db = Path(tempfile.mkdtemp(prefix="lm_reply_")) / "h.db"
    s = Store(db)
    s.add_message("m1", "10.0.0.2", "in", "mensagem original")
    s.add_message("m2", "10.0.0.2", "out", "minha resposta")
    s.set_reply("m2", "m1", "Ana", "mensagem original")
    got = s.get_reply("m2")
    assert got == {"id": "m1", "name": "Ana", "text": "mensagem original"}, got
    assert s.get_reply("m1") is None
    reps = s.replies_with("10.0.0.2")
    assert reps == {"m2": got}, reps
    assert s.replies_with("10.0.0.9") == {}
    print("OK banco (set/get/replies_with)")

    # 3. balão: citação renderiza com autor + trecho
    ctk.set_appearance_mode("Light")
    r = ctk.CTk()
    r.withdraw()
    try:
        host = ctk.CTkScrollableFrame(r, width=500, height=400)
        host.pack()
        row = app_gui.build_bubble(
            host, "out", "ok",
            app_gui.bubble_clock("out", "14/10/2026 - 08:12:33"),
            reply={"id": "m1", "name": "Ana", "text": "mensagem original"})
        texts = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, ctk.CTkLabel):
                    texts.append(str(c.cget("text")))
                walk(c)

        walk(row)
        assert "Ana" in texts, texts
        assert "mensagem original" in texts, texts
        assert "ok" in texts
        # sem reply: sem citação
        row2 = app_gui.build_bubble(host, "in", "só texto")
        texts2 = []

        def walk2(w):
            for c in w.winfo_children():
                if isinstance(c, ctk.CTkLabel):
                    texts2.append(str(c.cget("text")))
                walk2(c)

        walk2(row2)
        non_empty = [t for t in texts2 if t]
        assert "só texto" in non_empty and len(non_empty) == 1, texts2
        print("OK balão (citação visível; sem reply = label único)")
    finally:
        try:
            r.destroy()
        except Exception:
            pass

    # 4. barra de prévia: mostra e cancela
    class Lbl:
        def __init__(self):
            self.text = ""

        def configure(self, **kw):
            self.text = str(kw.get("text", ""))

    class Bar:
        packed = False

        def pack(self, **kw):
            self.packed = True

        def pack_forget(self):
            self.packed = False

    stub = type("S", (), {})()
    stub._reply = None
    stub._reply_lbl = Lbl()
    stub._reply_excerpt = Lbl()
    stub._reply_bar = Bar()
    stub.entry = type("E", (), {"focus_set": lambda self: None})()
    app_gui.ChatWindow._start_reply(stub, "m1", "Ana", "mensagem original")
    assert stub._reply == {"id": "m1", "name": "Ana", "text": "mensagem original"}
    assert stub._reply_lbl.text == "Respondendo a Ana"
    assert stub._reply_excerpt.text == "mensagem original"
    assert stub._reply_bar.packed is True
    app_gui.ChatWindow._clear_reply(stub)
    assert stub._reply is None and stub._reply_bar.packed is False
    print("OK prévia da resposta (mostrar/cancelar)")

    # 5. envio carrega a citação para a rede e para o banco
    sent: dict = {}
    real_send = chat.send_message
    real_log = app_gui.logger.log_message

    class Entry:
        def get(self, *a):
            return "minha resposta"

        def delete(self, *a):
            pass

    class Disc:
        def is_stale(self, ip):
            return False

    class Profile:
        def effective_display(self):
            return "Eder"

    class App:
        pass

    app = App()
    app.store = s
    app.settings = object()
    app.disc = Disc()
    app.profile = Profile()
    app.key = None
    app.selected_info = lambda ip: {"status": "online"}
    app.touch = lambda: None
    app.peer_label = lambda ip: "Ana"
    app.flush_outbox_soon = lambda: None

    cw = app_gui.ChatWindow.__new__(app_gui.ChatWindow)
    cw.app = app
    cw.ip = "10.0.0.2"
    cw.entry = Entry()
    cw._reply = {"id": "m1", "name": "Ana", "text": "mensagem original"}
    dated: list = []
    cw._dated = lambda *a, **k: dated.append((a, k))
    cw._clear_reply = lambda: setattr(cw, "_reply", None)

    def fake_send(ip, text, **kw):
        sent.update(kw)
        return "mid-30"

    chat.send_message = fake_send
    app_gui.logger.log_message = lambda *a, **k: None
    try:
        app_gui.ChatWindow.send(cw)
    finally:
        chat.send_message = real_send
        app_gui.logger.log_message = real_log
    assert sent.get("reply") == {"id": "m1", "name": "Ana",
                                 "text": "mensagem original"}, sent
    assert s.get_reply("mid-30") is not None
    assert dated and dated[0][1].get("reply") is not None
    assert cw._reply is None  # prévia limpa após enviar
    print("OK envio com citação (rede + banco + prévia limpa)")

    # 6. funções novas presentes
    for name in ("_bubble_menu", "_start_reply", "_clear_reply",
                 "_bind_bubble_menu", "_bubble_dblclick"):
        assert callable(getattr(app_gui.ChatWindow, name)), name
    print("OK metodos da resposta")

    # 7. duplo-clique dispara a resposta (v1.31)
    stub2 = type("S2", (), {})()
    stub2._reply = None
    got = {}

    def fake_start(mid, who, text):
        got.update({"id": mid, "name": who, "text": text})

    stub2._start_reply = fake_start
    stub2.app = type("A", (), {"peer_label": lambda s, ip: "Ana"})()
    stub2.ip = "10.0.0.2"
    row = type("R", (), {"_mid": "m9"})()
    app_gui.ChatWindow._bubble_dblclick(stub2, None, row, "in",
                                        "e aí?", "")
    assert got == {"id": "m9", "name": "Ana", "text": "e aí?"}, got
    # sem id (balão de sistema): não faz nada
    got.clear()
    app_gui.ChatWindow._bubble_dblclick(stub2, None, type("R2", (), {})(),
                                        "in", "x", "")
    assert got == {}, got
    print("OK duplo-clique responde")

    # 8. centralizar não recursa (crash v1.30: update_idletasks x after_idle)
    class FakeWin:
        calls = 0

        def update_idletasks(self):
            FakeWin.calls += 1
            if FakeWin.calls < 50:
                app_gui.center_window(self, None)  # reentra como o <Map>

        def winfo_width(self):
            return 100

        def winfo_height(self):
            return 100

        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

        def geometry(self, g):
            self.g = g

    fw = FakeWin()
    app_gui.center_window(fw, None)
    assert FakeWin.calls == 1, FakeWin.calls  # trava: só a 1ª chamada entra
    assert fw.g.startswith("+"), fw.g
    print("OK center_window sem recursao")

    print("TESTE REPLY: PASSOU")


if __name__ == "__main__":
    main()
