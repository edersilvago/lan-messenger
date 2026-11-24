"""Teste da 1.17: balões CustomTkinter (lados, cores, data, cartão).
Roda: python -m lan_messenger.test_bubbles
"""
from __future__ import annotations

import customtkinter as ctk

from lan_messenger import app_gui, chatview


def main() -> None:
    # 1. helpers puros: dois formatos de carimbo + lixo
    assert chatview.bubble_time("14/10/2026 - 08:12:33") == "08:12:33"
    assert chatview.bubble_time("2026-10-14 08:12:33") == "08:12:33"
    assert chatview.bubble_time("lixo") == ""
    assert chatview.bubble_time("") == ""
    assert chatview.date_label("14/10/2026 - 08:12:33") == "14 de outubro de 2026"
    assert chatview.date_label("2026-10-15 09:07:00") == "15 de outubro de 2026"
    assert chatview.date_label("sem-data") == ""
    assert chatview.format_size(1024 * 1024 * 1.2) == "1,2 MB"
    assert chatview.format_size(589 * 1024) == "589 KB"
    assert app_gui.bubble_clock("out", "14/10/2026 - 08:12:33") == "08:12:33 ✓"
    assert app_gui.bubble_clock("in", "14/10/2026 - 08:12:33") == "08:12:33"
    assert app_gui.status_pt("busy") == "ocupado"
    assert app_gui.status_pt("away") == "ausente"
    assert app_gui.status_pt("online") == "disponível"
    assert app_gui.status_pt("offline") == "offline"
    print("OK helpers (hora, data pt-BR, tamanho, tique)")

    ctk.set_appearance_mode("Light")
    r = ctk.CTk()
    r.withdraw()
    try:
        host = ctk.CTkScrollableFrame(r, width=500, height=400)
        host.pack()
        # 2. balões: verde direita / branco esquerda, cantos arredondados
        b_out = app_gui.build_bubble(host, "out", "Bom dia", "09:10 ✓")
        b_in = app_gui.build_bubble(host, "in", "bom dia", "09:07", name="Ana")
        bubbles = [w for w in host.winfo_children()]
        assert len(bubbles) == 2, len(bubbles)
        inner_out = [w for w in b_out.winfo_children()
                     if isinstance(w, ctk.CTkFrame)][0]
        inner_in = [w for w in b_in.winfo_children()
                    if isinstance(w, ctk.CTkFrame)][0]
        assert str(inner_out.cget("fg_color")) == str(("#D9FDD3", "#005C4B")), inner_out.cget("fg_color")
        assert str(inner_in.cget("fg_color")) == str(("#FFFFFF", "#1F2C34"))
        assert int(str(inner_out.cget("corner_radius"))) >= 10  # arredondado
        texts = " ".join(
            str(w.cget("text")) for b in (inner_out, inner_in)
            for w in b.winfo_children() if isinstance(w, ctk.CTkLabel))
        assert "Bom dia" in texts and "bom dia" in texts and "Ana" in texts
        assert "09:10 ✓" in texts and "09:07" in texts
        assert "09:07 ✓" not in texts  # recebido: sem tique
        print("OK balões (lados, cores, cantos, tique só no enviado)")

        # 3. pílula de data + cartão de anexo (largura fixa, texto inteiro)
        pill = app_gui.build_date_pill(host, "14 de outubro de 2026")
        assert "14 de outubro" in "".join(
            str(w.cget("text")) for w in pill.winfo_children()
            if isinstance(w, ctk.CTkLabel))
        card = app_gui.build_file_card(host, "Consulta SQL.txt",
                                       "07:39:07", "out",
                                       lambda: None)
        r.update()

        def _texts(w):
            out = []
            for k in w.winfo_children():
                if isinstance(k, ctk.CTkLabel):
                    out.append(str(k.cget("text")))
                elif isinstance(k, ctk.CTkButton):
                    out.append("BTN:" + str(k.cget("text")))
                out.extend(_texts(k))
            return out

        got = " ".join(_texts(card))
        assert "TXT" in got and "Consulta SQL.txt" in got, got
        assert "BTN:Abrir pasta" in got  # ação = botão (caminho não é link)
        assert "D:/" not in got and "pasta" not in got.replace("Abrir pasta", "")
        # nome inteiro com extensão (sem quebra por caractere)
        assert "Consulta SQL.txt" in got.replace("\n", " ")
        # 4. linha do histórico de arquivos (nome completo com extensão)
        line = app_gui.file_history_text("enviado", "Extrato.pdf", 1024 * 1200)
        assert line == "[arquivo enviado] Extrato.pdf (1,2 MB)", line
        print("OK pílula + cartão fixo + histórico de arquivos")

        # 4. texto longo/URL quebra sem erro
        long = "https://exemplo.com/" + "a" * 300 + " C:\\pasta\\arquivo.txt"
        app_gui.build_bubble(host, "in", long, "10:00")
        r.update()
        print("OK textos longos/URL/caminho")

        # 5. largura proporcional à janela (v1.32)
        class W:
            def __init__(self, width, top=None):
                self._w = width
                self._top = top

            def winfo_width(self):
                return self._w

            def winfo_toplevel(self):
                return self._top or self

        assert app_gui.bubble_max_w(W(1)) == 380          # sem medida: padrão
        assert app_gui.bubble_max_w(W(0)) == 380
        assert app_gui.bubble_max_w(W(600)) == 450        # 75% de 600
        assert app_gui.bubble_max_w(W(1920)) == 1200      # teto
        assert app_gui.bubble_max_w(W(300)) == 300        # piso (75% = 225)
        # sem medida própria: cai na janela pai
        assert app_gui.bubble_max_w(W(0, W(1000))) == 750
        # rewrap: rótulos marcados acompanham a nova largura
        n = app_gui.rewrap_bubbles(host, 600)
        assert n >= 2, n
        wraps = []

        def _collect(w):
            f = getattr(w, "_bubble_wrap", None)
            if f:
                wraps.append((w, f))
            for c in w.winfo_children():
                _collect(c)

        _collect(host)
        assert wraps, "nenhum rotulo marcado para rewrap"
        for lbl, frac in wraps:
            assert int(str(lbl.cget("wraplength"))) == max(120, int(600 * frac))
        assert app_gui.rewrap_bubbles(host, 600) == n     # mesmo valor: estável
        print(f"OK largura proporcional ({n} rotulos reajustados)")
        print("TESTE BUBBLES: PASSOU")
    finally:
        r.destroy()


if __name__ == "__main__":
    main()
