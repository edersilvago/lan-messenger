"""Janela principal estilo clássico em CustomTkinter + árvore por departamento.

Uso:  python -m lan_messenger.app_gui
Backend (protocolo, discovery, arquivos, banco) inalterado: só o visual
foi reconstruído em CustomTkinter.
"""
from __future__ import annotations

import queue
import os
import re
import threading
import time
import tkinter as tk
import traceback
import unicodedata
import uuid
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from . import (autostart, chat, config, crypto, discovery, files,
                history_view, logger, mass, networks, profile, remote, roster,
                sfx, single_instance, sysinfo, toaster, updates)
from . import chatview
from .store import Store

GITHUB_URL = "https://github.com/edersilvago/lan-messenger"

CRASH_LOG = config.APP_DATA / "logs" / "crash.log"


_CRASHING = False  # evita recursão no próprio log (crash dentro do log)


def log_crash(context: str, exc: BaseException | None = None) -> str:
    """Grava a exceção em logs/crash.log para análise. Nunca levanta.

    Formato: cabeçalho com data/hora + contexto, traceback completo e
    linha em branco. Devolve o caminho do arquivo (para a statusbar).
    """
    global _CRASHING
    if _CRASHING:  # recursão no log (pilha já no limite): não tenta gravar
        return str(CRASH_LOG)
    _CRASHING = True
    try:
        CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} [{context}] ---\n")
            if exc is not None:
                traceback.print_exception(type(exc), exc, exc.__traceback__,
                                          file=f)
            f.write("\n")
    except Exception:
        pass
    finally:
        _CRASHING = False
    return str(CRASH_LOG)


def flush_outbox(store, is_online, send, on_delivered=None) -> list[str]:
    """Tenta entregar a fila de saída (v1.29). Devolve os ids entregues.

    is_online(peer) decide se vale tentar agora; send(peer, text, msg_id)
    levanta exceção quando não entrega. Nunca levanta: uma falha não para
    as outras mensagens da fila.
    """
    done: list[str] = []
    try:
        pend = store.pending_messages()
    except Exception as e:
        log_crash("outbox_list", e)
        return done
    for mid, peer, text in pend:
        try:
            if not is_online(peer):
                continue
            send(peer, text, mid)
        except Exception:
            continue
        try:
            store.drop_pending(mid)
        except Exception as e:
            log_crash("outbox_drop", e)
            continue
        done.append(mid)
        if on_delivered is not None:
            try:
                on_delivered(mid, peer, text)
            except Exception as e:
                log_crash("outbox_cb", e)
    return done


try:
    from . import tray as tray_mod
except ImportError:
    tray_mod = None


def send_binding_allows(key: str, send_key: str) -> bool:
    """Enter envia se send_key=='enter'; Ctrl+Enter envia se 'ctrl_enter'."""
    if key == "Return":
        return send_key == "enter"
    if key == "Control-Return":
        return send_key == "ctrl_enter"
    return False


HELP_TEXT = """LAN Messenger - Ajuda completa (uso e funcionalidades)

1. COMEÇANDO
1.1 Minhas Informações: preencha nome (exibido na lista), departamento
(grupo na lista), cargo, AnyDesk ID e RustDesk ID. O botão "Detectar IDs"
lê os IDs desta máquina sozinho. O botão OK fica sempre visível no rodapé.
1.2 Rede (VPN): cadastre as faixas dos dois lados, ex 10.0.0.1-10.0.0.254 e
192.168.30.1-192.168.30.254. Gere a chave (Gerar/Salvar) e distribua o mesmo
valor aos demais PCs (Exportar/Importar).
1.3 Aguarde alguns segundos: os colegas aparecem agrupados por departamento.
Use "Atualizar Lista de Usuários" (botão direito no vazio) para forçar.

2. LISTA DE USUÁRIOS (fidelidade)
- Verde = online, amarelo = ausente, vermelho = ocupado, cinza = offline.
- "Ocultar usuários offline" (botão direito no vazio) esconde os cinzas.
- "(sinal fraco)" = online mas sem beacon há +20s (UDP perdendo na VPN);
ainda dá para conversar, mas confira firewall/VPN.
- Offline some dos online e fica no histórico cinza. Ao fechar o app ele
avisa os colegas na hora (não espera o timeout).
- Ver Informações mostra IP, status, "Visto há", IDs remotos e hardware
(sistema, processador, RAM, disco).

3. CONVERSANDO
- Balões: recebidas em branco à esquerda, enviadas em verde à direita,
com HH:MM:SS sempre dentro do balão; tique único cinza = entregue no app
do colega (sem tique azul: o sistema não informa leitura). Separadores de
data agrupam o histórico ("14 de outubro de 2026"; desligável em
Config > Mensagens).
- Links http:// ou www. na mensagem viram azul clicável e abrem no
navegador (a pontuação final da frase não entra no link).
- Anexos aparecem em cartão (selo, nome, pasta/tamanho, hora) com botão
"Abrir pasta".
- Duplo-clique ou Enter abre a conversa. Enter envia (ou Ctrl+Enter,
conforme Config > Atalhos).
- "Convidar" chama outro usuário. "Enviar Arquivo(s)" ou arrastar/soltar
envia arquivos, com barra de progresso e Cancelar. Ctrl+V com print na
área de transferência envia o print como PNG.
- Botões no topo da conversa: informações, AnyDesk, RustDesk.
- Se o destino estiver offline, a mensagem fica na fila local (balão com
"(pendente)") e sai sozinha quando o contato aparecer online — o remetente
precisa estar com o app aberto nessa hora. Sem fila no servidor: ninguém
recebe com tudo desligado.
- Responder a uma mensagem específica: botão direito no balão >
"Responder" (ou duplo-clique na mensagem); a citação (autor + trecho)
aparece dentro do balão enviado com barra verde, estilo WhatsApp. A
prévia fica acima do campo de texto (✕ cancela).
- Config > Mensagens > Tamanho da Fonte: digite qualquer valor inteiro
entre 8 e 32 px. A mudança altera imediatamente mensagens, links,
citações, nomes, horários, datas, avisos e anexos nas conversas 1-1 e
em grupo.
- ENTER não espera rede: a mensagem é exibida e enfileirada na hora; o
envio ocorre em segundo plano, com status no rodapé. Clique em área
livre da conversa foca o campo de texto.
- Palavras longas sem espaço quebram automaticamente no balão.
- Atalhos de texto viram emoji após envio: :) :D :( ;) :P <3 :O :/ :'( (y) (n).
- Mensagem em massa: marca grupos/usuários com caixas de seleção,
Todos/Nenhum.
- Conversa em grupo: janela por departamento, recebe os broadcasts.

4. ARQUIVOS
- Recebimento automático (ou "Perguntar antes" em Config > Transferência).
- Barra mostra progresso; "Abrir pasta" abre a pasta de entrada no Explorer.
- Pasta padrão: %APPDATA%\\LANMessenger\\inbox (mudável na Config).

5. STATUS
- Rodapé: Disponível aplica direto; Ocupado/Ausente abrem a Mensagem de
status com contagem de 10s ("Definir Status [10]" confirma sozinho).
A mensagem viaja no beacon e aparece para os colegas (Informações e
topo da conversa). Manual não volta sozinho.
- Ausência automática após inatividade (Config > Geral), só se não manual.
- Tray tem o mesmo menu de status; ícone fica visível com a janela aberta.

6. ACESSO REMOTO
- AnyDesk/RustDesk: IDs viajam no beacon. Botão direito > Conectar abre o
app remoto direto no ID. Sem ID, o app avisa para cadastrar.
- Ping (CMD: 5 disparos) testa a rota até o IP do contato.

7. PROBLEMAS (colega não aparece / some e volta)
- Confira ping entre as redes, firewall (UDP 50000, TCP 50001/50002) nos
DOIS lados e as faixas na tela Rede. Mesma chave nos dois lados.
- Tela Rede > Diagnóstico: escuta UDP OK? último recebido? Testar IP?
Testar OK + lista vazia = UDP bloqueado (firewall/VPN) — use +IP manual.
- "Sinal fraco" frequente = perda UDP no túnel: reduza interferência,
libere UDP 50000 no firewall da VPN ou use IPs manuais. A partir da v1.14
o app confirma presença também por TCP (porta do chat): se o TCP passa,
o colega volta sozinho em segundos, mesmo com o UDP bloqueado — sem
precisar fechar e abrir o app.
- Sem rota/TCP = mensagem falha na hora com aviso (não fica pendente).
- Erro interno: o app grava data, hora e traceback em
%APPDATA%\\LANMessenger\\logs\\crash.log (Config > Log >
"Abrir pasta do log de erros"). Envie esse arquivo ao suporte.

8. HISTÓRICO DE VERSÕES
- v1.0/v1.1: base P2P (descoberta UDP, chat TCP, arquivos, presença,
histórico local, instaladores).
- v1.2: descoberta imediata, firewall em todos os perfis, instalador
idempotente.
- v1.3: Ping no contato, massa com checkboxes, menu e conversa em grupo,
Geral padrão, arrastar/soltar, progresso e "Abrir pasta".
- v1.4: geometria lembrada, Ping no CMD, AnyDesk/RustDesk, instalador
fecha versão aberta, conversa à frente.
- v1.5: update forçado, massa fiel no grupo, auto-detecção de IDs,
"Abrir pasta" no log, suporte no Sobre.
- v1.6: grupo não recolhe sozinho, "Abrir pasta" clicável, conversas
650x620.
- v1.7: inbox no "Abrir pasta", massa responsiva, sons WAV, mínimos.
- v1.8: tray sempre ativo, botões de status.
- v1.9: hardware do contato, cores na lista, Ctrl+V com print, janelas
centralizadas, atalhos na conversa.
- v1.10: centro no desktop, marcadores Win7, SO/build.
- v1.11: presença estável, trava anti-offline, Minhas Informações com OK.
- v1.12: histórico na conversa, status com regressiva, versículo no
Sobre, versão no exe.
- v1.13: botões de status coloridos, setups com versão no nome.
- v1.14: presença via TCP (volta sozinha após queda da VPN, sem
reiniciar; cache de colegas).
- v1.15: conversa em balões (recebidas à esquerda, enviadas à direita,
com data/hora embaixo).
- v1.16: balões WhatsApp (verde/branco, hora dentro, tique de entregue),
separadores de data e anexos em cartão.
- v1.17: visual reconstruído em CustomTkinter (balões arredondados).
- v1.18: centralização e fim do histórico, cores na lista, botão da
pasta, barra responsiva e temas Light/Dark.
- v1.19: centralização pós-layout, status com botões fixos, grupos
brancos no Dark e versão do colega nas Informações.
- v1.20: status em linha própria, tudo em português, HH:MM:SS nos
balões e tray sem duplicata.
- v1.21: carimbo HH:MM:SS sempre visível no balão.
- v1.22: cartão de anexo tamanho de balão + arquivos no histórico.
- v1.23: menu de botão direito na principal + inbox por remetente.
- v1.24: emojis nas conversas + eu na lista (anotações).
- v1.25: limpeza de referências a marca de terceiros (mensagens e
comentários internos); sem mudança de comportamento.
- v1.26: notificações do sistema (toast no Win10/11), menções @nome na
conversa em grupo e link do projeto no Ajuda/Sobre.
- v1.27: links http(s)/www. nas mensagens viram clicáveis no balão.
- v1.28: log de erros em logs\\crash.log (data, hora e traceback) e
diálogos de falha substituídos por aviso no rodapé.
- v1.29: mensagem para contato offline fica na fila local e é entregue
sozinha quando ele aparece online (tique troca de "(pendente)" p/ ✓).
- v1.30: responder mensagem específica — citação no balão com barra
verde (autor + trecho), prévia acima do campo de texto.
- v1.31: duplo-clique na mensagem também responde; citação do balão
com altura/espelho ajustados; correção de travamento ao centralizar
janelas.
- v1.32: texto dos balões proporcional à janela (75% da largura, com
reajuste automático ao redimensionar).
- v1.33: correção definitiva do erro "maximum recursion depth exceeded"
ao abrir ou rolar conversas; callbacks Tk não executam mais eventos
pendentes dentro de outros callbacks.
- v1.34: balões usam 94% da conversa sem teto fixo; citação compacta
(48–80 px); abrir/maximizar preserva área visível e posição da rolagem.
- v1.35: Tamanho da Fonte passa a alterar todos os textos da conversa,
inclusive balões já abertos; layout validado de 620 px até 4K.
- v1.36: fonte deixa de ter três opções fixas; campo numérico aceita
qualquer tamanho inteiro entre 8 e 32 px, com prévia instantânea.
- v1.37: envio não bloqueia mais a UI (TCP/ACK no worker); clique na
conversa foca a digitação; aviso silencioso de nova versão.
- v1.38: ao abrir conversa, janela e campo de texto recebem foco real;
notificação nova mensagem traz a conversa para frente e foca digitação.
- v1.39: quebra automática de palavras longas nos balões; atalhos de
texto viram emoji após envio (sem alterar URLs).

9. PROJETO
- Código-fonte, documentação e releases no GitHub:
  https://github.com/edersilvago/lan-messenger
  (aba "Releases" tem os instaladores de cada versão)
"""


# rótulo de presença em português (nunca exibir "busy"/"away" crus)
STATUS_PT = {"online": "disponível", "busy": "ocupado",
             "away": "ausente", "offline": "offline"}


def status_pt(status: str) -> str:
    return STATUS_PT.get(str(status or "online"), str(status))


# cores do balão mencionado (claro, escuro) — leve toque amarelo
MENTION_BG = ("#FFF6DE", "#3D3517")
MENTION_NAME_FG = ("#B45309", "#FFB74D")


def _norm_name(s: str) -> str:
    """minúsculas + sem acento: 'José' == 'jose'."""
    return unicodedata.normalize("NFKD", s).encode(
        "ascii", "ignore").decode("ascii").lower()


def mentioned_me(text: str, display: str, user: str = "") -> bool:
    """True se a mensagem contém @<nome> meu (comparação sem acento/caixa).

    Aceita nome de exibição ("@Eder Silva") e usuário ("@eder"). Não casa
    prefixo: "@joaozinho" não menciona "joao".
    """
    tokens = {_norm_name(t) for t in (display, user) if t and t.strip()}
    if not tokens:
        return False
    norm = _norm_name(str(text or ""))
    for tok in tokens:
        if re.search("@" + re.escape(tok) + r"(?![\w.-])", norm):
            return True
    return False


# cor do nome por status (claro, escuro) — volta das cores na lista
ROSTER_STATUS_COLORS = {
    "online": ("#087a22", "#66BB6A"),
    "busy": ("#b00020", "#EF5350"),
    "away": ("#b26a00", "#FFCA28"),
    "offline": ("#777777", "#9E9E9E"),
}


# (emoji-fallback, dica, método do App, ícone em assets/)
TOOLBAR_BUTTONS = [
    ("💬", "Conversa", "open_selected", "conversa.png"),
    ("📢", "Mensagem em massa", "mass_dialog", "massa.png"),
    ("📁", "Arquivos recebidos", "open_inbox", "arquivos.png"),
    ("📜", "Histórico", "open_history", "historico.png"),
    ("👤", "Minhas informações", "my_data_dialog", "minhas.png"),
    ("🌐", "Rede", "edit_ranges", "rede.png"),
    ("⚙", "Configurações", "general_dialog", "config.png"),
    ("❓", "Ajuda e Sobre", "about_dialog", "ajuda.png"),
]

STATUS_COLORS = {"online": ("#e8f5e9", "#1B5E20"),
                 "busy": ("#ffebee", "#7F0000"),
                 "away": ("#fff8e1", "#5D4037")}

BUBBLE_IN_BG = ("#FFFFFF", "#1F2C34")  # recebido: branco
BUBBLE_OUT_BG = ("#D9FDD3", "#005C4B")  # enviado: verde
BUBBLE_FG = ("#202124", "#E9EDEF")      # texto
BUBBLE_TS_FG = ("#667085", "#8696A0")  # horário discreto
BUBBLE_NAME_FG = ("#555555", "#AEBAC1")
BUBBLE_LOG_BG = ("#ECE5DD", "#0B141A")  # fundo do histórico
BUBBLE_SEP_BG = ("#DDE4EA", "#1F2C34")
BUBBLE_SEP_FG = ("#54656F", "#AEBAC1")
LINK_BLUE = ("blue", "#53BDEB")
TICK_DELIVERED = "✓"


def _tooltip(widget: tk.Widget, text: str) -> None:
    """Balão flutuante estilo clássico (ex 'Configurações')."""
    tip: list = []

    def show(_e=None) -> None:
        hide()
        try:
            x = widget.winfo_rootx() + 8
            y = widget.winfo_rooty() + widget.winfo_height() + 2
            w = tk.Toplevel(widget)
            w.wm_overrideredirect(True)
            w.wm_geometry(f"+{x}+{y}")
            tk.Label(w, text=text, background="#ffffe1", relief="solid",
                     borderwidth=1, padx=4, pady=2).pack()
            tip.append(w)
        except tk.TclError:
            pass

    def hide(_e=None) -> None:
        while tip:
            try:
                tip.pop().destroy()
            except tk.TclError:
                pass
    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<ButtonPress>", hide, add="+")


def flash_window(widget: tk.Misc) -> bool:
    """Pisca o botão da janela na barra de tarefas (novas conversas)."""
    try:
        import ctypes

        class _FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint),
                        ("hwnd", ctypes.c_void_p),
                        ("dwFlags", ctypes.c_uint),
                        ("uCount", ctypes.c_uint),
                        ("dwTimeout", ctypes.c_uint)]
        info = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), widget.winfo_id(), 3, 5, 0)
        return bool(ctypes.windll.user32.FlashWindowEx(ctypes.byref(info)))
    except Exception:
        return False


def center_window(win: tk.Misc, parent: tk.Misc | None = None) -> None:
    """Centraliza sem rodar callbacks Tk dentro de outro callback.

    Nunca use update/update_idletasks aqui: eles podem reexecutar o
    próprio after em andamento e causar RecursionError.
    """
    try:
        w, h = win.winfo_width(), win.winfo_height()
        if w <= 1:
            w = win.winfo_reqwidth()
        if h <= 1:
            h = win.winfo_reqheight()
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
    except tk.TclError:
        pass
    except Exception as e:
        log_crash("center_window", e)


def esc_closes(win: tk.Misc, action) -> None:
    """ESC sai da janela (todas as telas do software)."""
    try:
        win.bind("<Escape>", lambda _e: action(), add="+")
    except tk.TclError:
        pass


def make_root():
    """Raiz CustomTkinter + arrastar-soltar quando disponível."""
    try:
        _theme = profile.load()[1].theme
    except Exception:
        _theme = "Light"
    if _theme not in ("Light", "Dark", "System"):
        _theme = "Light"
    ctk.set_appearance_mode(_theme)
    ctk.set_default_color_theme("blue")
    try:
        from tkinterdnd2 import TkinterDnD

        class _Root(ctk.CTk, TkinterDnD.DnDWrapper):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.TkdndVersion = TkinterDnD._require(self)

        return _Root()
    except Exception:
        return ctk.CTk()


def ctk_dialog(parent: tk.Misc, title: str, geom: str,
               resizable: tuple[bool, bool] = (False, False)):
    """CTkToplevel centralizada + ESC + ícone."""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    center_fixed(win, geom)
    try:
        win.resizable(*resizable)
    except tk.TclError:
        pass
    esc_closes(win, win.destroy)
    ico = config.asset_path("app.ico")
    if ico:
        try:
            win.iconbitmap(ico)
        except tk.TclError:
            pass
    try:
        win.grab_set()
    except tk.TclError:
        pass
    return win


def scroll_end(scroll) -> None:
    """Rola ao fim após duas fases do layout, sem eventos recursivos."""
    def _go(final: bool = False) -> None:
        try:
            canvas = scroll._parent_canvas
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
            canvas.yview_moveto(1.0)
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:  # frame destruído no meio do after
            log_crash("scroll_end", e)
        if final:
            try:
                scroll._scroll_end_jobs = []
            except Exception:
                pass

    try:
        for old in getattr(scroll, "_scroll_end_jobs", []):
            scroll.after_cancel(old)
        scroll._scroll_end_jobs = [
            scroll.after(80, _go),
            scroll.after(320, lambda: _go(True)),
        ]
    except (tk.TclError, AttributeError):
        pass


def center_fixed(win: tk.Misc, geom: str) -> None:
    """Centraliza usando o WxH conhecido (vale antes do conteúdo existir)."""
    try:
        w, h = chatview.geometry_size(geom)
        if not w or not h:
            center_window(win, None)
            return
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
    except tk.TclError:
        pass
    except Exception as e:
        log_crash("center_fixed", e)


def center_soon(win: tk.Misc) -> None:
    """Centraliza uma vez após o layout, sem <Map>/after_idle recursivo."""
    try:
        old = getattr(win, "_center_job", None)
        if old is not None:
            win.after_cancel(old)
        win._center_job = win.after(80, lambda: center_window(win, None))
    except (tk.TclError, AttributeError):
        pass


# link dentro do balão (claro, escuro) — azul clicável
BUBBLE_LINK_FG = ("#1A5FB4", "#8AB4F8")
# citação de resposta (v1.30): barra verde WhatsApp + fundo suave
REPLY_QUOTE_BG = ("#EDEFF2", "#2A343A")      # dentro do balão recebido
REPLY_QUOTE_BG_OUT = ("#C8EFC2", "#01483C")  # dentro do balão enviado
REPLY_QUOTE_BAR = ("#00A884", "#00A884")
REPLY_QUOTE_NAME = ("#008069", "#00A884")
REPLY_QUOTE_FG = ("#667085", "#AEBAC1")

URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)


def open_url(url: str) -> None:
    """Abre link no navegador padrão; www. sem esquema ganha https://."""
    if url.lower().startswith("www."):
        url = "https://" + url
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass


def clean_url(url: str) -> str:
    """Tira pontuação final do link ('fim da frase.', ')' sem par aberto)."""
    while url and url[-1] in ".,;:!?":
        url = url[:-1]
    if url.endswith(")") and "(" not in url:
        url = url[:-1]
    return url


def soft_break(text: str, chunk: int = 30) -> str:
    """Insere quebra invisível em sequências longas sem espaços (v1.39)."""
    if not text:
        return str(text or "")
    out: list[str] = []
    run = 0
    for ch in str(text):
        out.append(ch)
        if ch.isspace():
            run = 0
        else:
            run += 1
            if run >= chunk:
                out.append("\u200b")
                run = 0
    return "".join(out)


def split_url_segments(text: str) -> list[tuple[str, str]]:
    """Divide texto em segmentos ("text"|"url", conteúdo) para links clicáveis.

    Sem URL na mensagem: [("text", texto)] — balão segue com um label só.
    """
    text = str(text or "")
    hits = list(URL_RE.finditer(text))
    if not hits:
        return [("text", text)]
    segs: list[tuple[str, str]] = []
    pos = 0
    for m in hits:
        url = clean_url(m.group(0))
        end = m.start() + len(url)  # pontuação final fica no texto
        if m.start() > pos:
            segs.append(("text", text[pos:m.start()]))
        segs.append(("url", url))
        pos = end
    if pos < len(text):
        segs.append(("text", text[pos:]))
    return segs


def bubble_max_w(parent: tk.Misc) -> int:
    """Largura de quebra do balão proporcional à janela (v1.32).

    94% da largura real, mínimo 300 px: texto longo usa quase toda a
    conversa em qualquer tamanho, sem teto fixo na janela maximizada.
    """
    w = 0
    try:
        w = parent.winfo_width()
    except Exception:
        w = 0
    if w <= 1:
        try:
            w = parent.winfo_toplevel().winfo_width()
        except Exception:
            w = 0
    if w <= 1:
        return 380
    return max(300, int(w * 0.94))


def _chat_role(widget, role: str):
    """Marca widget cujo tamanho acompanha Configurações > Mensagens."""
    try:
        widget._chat_font_role = role
    except Exception:
        pass
    return widget


def quote_height(text_len: int, wrap: int, font_px: int) -> int:
    """Altura compacta da citação para 1–3 linhas e fonte atual."""
    char_px = max(5, round(font_px * 0.55))
    chars = max(20, wrap // char_px)
    lines = max(1, min(3, (text_len + chars - 1) // chars))
    return 20 + (font_px + 1) * 2 + (lines - 1) * (font_px + 3)


def build_bubble(parent: tk.Misc, direction: str, text: str, clock: str = "",
                 name: str = "", max_w: int | None = None, mention: bool = False,
                 reply: dict | None = None, font_px: int = 13):
    """Balão arredondado (in=esquerda branca, out=direita verde).

    clock: "08:12" (recebida) ou "08:12 ✓" (enviada: entregue via ACK;
    nunca azul — o sistema não informa leitura).
    mention: mensagem de grupo que me menciona (@nome) — fundo amarelado
    e nome em laranja com "— mencionou você".
    reply: cita mensagem específica (v1.30) — bloco com barra verde,
    nome do autor e trecho, no topo do balão (estilo WhatsApp).
    max_w: None = calcula pela largura da janela (v1.32).
    """
    if max_w is None:
        max_w = bubble_max_w(parent)
    side = "e" if direction == "out" else "w"
    bg = MENTION_BG if (mention and direction == "in") else (
        BUBBLE_OUT_BG if direction == "out" else BUBBLE_IN_BG)
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=8, pady=3)
    bubble = ctk.CTkFrame(row, corner_radius=14, fg_color=bg)
    bubble.pack(side="right" if side == "e" else "left",
                anchor="e" if side == "e" else "w")
    if name and direction == "in":
        name_lbl = _chat_role(ctk.CTkLabel(
            bubble, text=f"{name} — mencionou você" if mention else name,
            text_color=MENTION_NAME_FG if mention else BUBBLE_NAME_FG,
            font=ctk.CTkFont(size=max(8, font_px - 2), weight="bold"),
            anchor="w"), "name")
        name_lbl.pack(fill="x", padx=12, pady=(8, 0))
    if reply:
        # citação no topo do balão (v1.30): barra verde + autor + trecho
        # largura própria (não puxa o balão: wraplength curto + 1 linha)
        qbg = REPLY_QUOTE_BG_OUT if direction == "out" else REPLY_QUOTE_BG
        qname = str(reply.get("name", ""))[:40]
        raw_qtext = str(reply.get("text", ""))
        qtext = raw_qtext[:140]
        if len(raw_qtext) > 140:
            qtext += "…"
        qtext = soft_break(qtext)
        qwrap = max(160, int(max_w * 0.88))
        quote_h = quote_height(len(qtext), qwrap, font_px)
        quote = ctk.CTkFrame(bubble, fg_color=qbg, corner_radius=6,
                             height=quote_h)
        quote.pack_propagate(False)
        quote.pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkFrame(quote, fg_color=REPLY_QUOTE_BAR, width=4,
                     corner_radius=2).pack(side="left", fill="y",
                                           padx=(5, 0), pady=4)
        qin = ctk.CTkFrame(quote, fg_color="transparent",
                           height=quote_h - 8)
        qin.pack_propagate(False)
        qin.pack(fill="x", padx=(3, 7), pady=(4, 5))
        qname_lbl = _chat_role(ctk.CTkLabel(
            qin, text=qname, text_color=REPLY_QUOTE_NAME,
            font=ctk.CTkFont(size=max(8, font_px - 2), weight="bold"),
            anchor="w"), "quote_name")
        qname_lbl.pack(fill="x")
        qlbl = _chat_role(ctk.CTkLabel(
            qin, text=qtext, text_color=REPLY_QUOTE_FG,
            font=ctk.CTkFont(size=max(8, font_px - 1)), anchor="w",
            justify="left", wraplength=qwrap), "quote")
        qlbl.pack(fill="x")
        try:
            qlbl._bubble_wrap = 0.88  # reajusta ao redimensionar (v1.34)
            qlbl._quote_frame = quote
            qlbl._quote_body = qin
            qlbl._quote_text_len = len(qtext)
            qlbl._quote_font_px = font_px
        except Exception:
            pass
    segs = split_url_segments(text)
    if len(segs) == 1 and segs[0][0] == "text":
        lbl = _chat_role(ctk.CTkLabel(
            bubble, text=soft_break(text), text_color=BUBBLE_FG,
            font=ctk.CTkFont(size=font_px), anchor="w",
            justify="left", wraplength=max_w), "body")
        lbl.pack(fill="x", padx=12, pady=(4, 0))
        try:
            lbl._bubble_wrap = 1.0
        except Exception:
            pass
    else:
        # texto com link: segmentos em linhas; URL azul e clicável
        for kind, content in segs:
            shown = soft_break(content)
            if kind == "url":
                lk = _chat_role(ctk.CTkLabel(
                    bubble, text=shown, text_color=BUBBLE_LINK_FG,
                    font=ctk.CTkFont(size=font_px, underline=True),
                    anchor="w", justify="left",
                    wraplength=max_w, cursor="hand2"), "link")
                lk.pack(fill="x", padx=12, pady=(4, 0))
                lk.bind("<Button-1>", lambda _e, u=content: open_url(u))
                try:
                    lk._bubble_wrap = 1.0
                except Exception:
                    pass
            else:
                lb = _chat_role(ctk.CTkLabel(
                    bubble, text=shown, text_color=BUBBLE_FG,
                    font=ctk.CTkFont(size=font_px), anchor="w",
                    justify="left", wraplength=max_w), "body")
                lb.pack(fill="x", padx=12, pady=(4, 0))
                try:
                    lb._bubble_wrap = 1.0
                except Exception:
                    pass
    if clock:
        ts_lbl = _chat_role(ctk.CTkLabel(
            bubble, text=clock, text_color=BUBBLE_TS_FG,
            font=ctk.CTkFont(size=max(8, font_px - 3)), anchor="e"), "clock")
        ts_lbl.pack(fill="x", padx=12, pady=(0, 8))
        try:
            row._clock_label = ts_lbl  # v1.29: p/ virar tique ao entregar
        except Exception:
            pass
    else:
        ctk.CTkLabel(bubble, text="", font=ctk.CTkFont(size=4)).pack(pady=(0, 6))
    return row


def rewrap_bubbles(scroll, max_w: int | None = None) -> int:
    """Reajusta o wraplength de todos os balões à largura atual (v1.32).

    Volta quantos rótulos foram ajustados. Nunca levanta: janela no
    meio do fechamento é ignorada.
    """
    if max_w is None:
        max_w = bubble_max_w(scroll)
    n = 0
    stack = [scroll]
    while stack:
        w = stack.pop()
        frac = getattr(w, "_bubble_wrap", None)
        if frac:
            try:
                wrap = max(120, int(max_w * float(frac)))
                w.configure(wraplength=wrap)
                quote = getattr(w, "_quote_frame", None)
                body = getattr(w, "_quote_body", None)
                if quote is not None and body is not None:
                    size = int(getattr(w, "_quote_text_len", 1))
                    px = int(getattr(w, "_quote_font_px", 13))
                    height = quote_height(size, wrap, px)
                    quote.configure(height=height)
                    body.configure(height=height - 8)
                n += 1
            except (tk.TclError, ValueError):
                pass
        try:
            stack.extend(w.winfo_children())
        except tk.TclError:
            pass
    return n


def apply_chat_fonts(scroll, font_px: int) -> int:
    """Aplica tamanho configurado a todos os textos já renderizados."""
    specs = {
        "body": (font_px, "normal", False),
        "link": (font_px, "normal", True),
        "name": (max(8, font_px - 2), "bold", False),
        "quote": (max(8, font_px - 1), "normal", False),
        "quote_name": (max(8, font_px - 2), "bold", False),
        "clock": (max(8, font_px - 3), "normal", False),
        "date": (max(8, font_px - 2), "normal", False),
        "system": (max(8, font_px - 2), "normal", False),
        "file_name": (font_px, "bold", False),
        "file_meta": (max(7, font_px - 2), "normal", False),
        "file_link": (max(7, font_px - 2), "normal", True),
    }
    n = 0
    stack = [scroll]
    while stack:
        widget = stack.pop()
        role = getattr(widget, "_chat_font_role", "")
        if role in specs:
            size, weight, underline = specs[role]
            try:
                widget.configure(font=ctk.CTkFont(
                    size=size, weight=weight, underline=underline))
                if role == "quote":
                    widget._quote_font_px = font_px
                n += 1
            except (tk.TclError, ValueError):
                pass
        try:
            stack.extend(widget.winfo_children())
        except tk.TclError:
            pass
    rewrap_bubbles(scroll)
    return n


def bind_rewrap(win: tk.Misc, scroll) -> None:
    """Ao redimensionar a janela, requebra o texto dos balões (v1.32).

    Debounce de 200 ms: <Configure> dispara a cada movimento do mouse.
    """
    state = {"job": None, "w": 0, "restore": []}

    def _go() -> None:
        state["job"] = None
        try:
            w = bubble_max_w(scroll)
            canvas = scroll._parent_canvas
            view = canvas.yview()
        except tk.TclError:
            return
        if w == state["w"]:
            return
        state["w"] = w
        at_bottom = not view or view[1] >= 0.98
        first = view[0] if view else 1.0
        rewrap_bubbles(scroll, w)

        def _restore(final: bool = False) -> None:
            try:
                bbox = canvas.bbox("all")
                if bbox:
                    canvas.configure(scrollregion=bbox)
                canvas.yview_moveto(1.0 if at_bottom else first)
            except tk.TclError:
                pass
            if final:
                state["restore"] = []

        for old in state["restore"]:
            try:
                win.after_cancel(old)
            except tk.TclError:
                pass
        try:
            state["restore"] = [
                win.after(60, _restore),
                win.after(280, lambda: _restore(True)),
            ]
        except tk.TclError:
            state["restore"] = []

    def _on(_e=None) -> None:
        # Toplevel recebe <Configure> dos filhos também. Só sua largura conta.
        if _e is not None and getattr(_e, "widget", win) is not win:
            return
        if state["job"] is not None:
            try:
                win.after_cancel(state["job"])
            except tk.TclError:
                pass
        try:
            state["job"] = win.after(200, _go)
        except tk.TclError:
            state["job"] = None

    try:
        win.bind("<Configure>", _on, add="+")
    except tk.TclError:
        pass


def build_date_pill(parent: tk.Misc, label: str, font_px: int = 13):
    """Pílula de data centralizada ("14 de outubro de 2026")."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=8, pady=6)
    pill = _chat_role(ctk.CTkLabel(
        row, text=label, fg_color=BUBBLE_SEP_BG,
        text_color=BUBBLE_SEP_FG, corner_radius=10,
        font=ctk.CTkFont(size=max(8, font_px - 2)), padx=12, pady=4), "date")
    pill.pack(anchor="center")
    return row


CARD_EXT_COLORS = {
    "pdf": "#E5484D", "doc": "#2B579A", "docx": "#2B579A",
    "xls": "#217346", "xlsx": "#217346", "ppt": "#D24726",
    "pptx": "#D24726", "zip": "#B26A00", "rar": "#B26A00",
    "7z": "#B26A00", "png": "#6A5ACD", "jpg": "#6A5ACD",
    "jpeg": "#6A5ACD", "gif": "#6A5ACD", "bmp": "#6A5ACD",
    "mp4": "#553C9A", "mp3": "#0E7490", "wav": "#0E7490",
    "txt": "#5F6368", "csv": "#217346",
}


CARD_WIDTH = 360  # largura fixa: não colapsa como o layout aninhado
CARD_NAME_CHARS = 40  # quebra manual: wraplength do CTkLabel é instável aqui


def build_file_card(parent: tk.Misc, name: str, clock: str,
                    direction: str, open_cmd, px: int = 11):
    """Cartão tamanho de balão de texto: selo + nome + hora + Abrir pasta.

    Só nome+extensão e ícone (sem pasta/caminho). open_cmd: ação já
    existente (ex abrir a pasta). Sem ação validada, nada vira link.
    """
    bg = BUBBLE_OUT_BG if direction == "out" else BUBBLE_IN_BG
    side = "e" if direction == "out" else "w"
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=8, pady=3)
    card = ctk.CTkFrame(row, corner_radius=14, fg_color=bg,
                        width=CARD_WIDTH, height=96)
    try:
        card.pack_propagate(False)
    except tk.TclError:
        pass
    card.pack(side="right" if side == "e" else "left",
              anchor="e" if side == "e" else "w")
    ext = (name.rsplit(".", 1)[-1].lower() if "." in name else "?")[:4]
    color = CARD_EXT_COLORS.get(ext, "#5F6368")
    badge = ctk.CTkLabel(card, text=ext.upper() or "FILE", fg_color=color,
                         text_color="white", corner_radius=8,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         width=52, height=52)
    badge.pack(side="left", padx=(10, 8), pady=10)
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
    import textwrap as _tw
    wrapped_name = "\n".join(_tw.wrap(name, CARD_NAME_CHARS) or [name])
    file_name = _chat_role(ctk.CTkLabel(
        body, text=wrapped_name, text_color=BUBBLE_FG,
        font=ctk.CTkFont(size=px, weight="bold"),
        anchor="w", justify="left"), "file_name")
    file_name.pack(fill="x")
    foot = ctk.CTkFrame(body, fg_color="transparent")
    foot.pack(fill="x", pady=(6, 0))
    if clock:
        file_clock = _chat_role(ctk.CTkLabel(
            foot, text=clock, text_color=BUBBLE_TS_FG,
            font=ctk.CTkFont(size=max(7, px - 2))), "file_meta")
        file_clock.pack(side="left")
    file_link = _chat_role(ctk.CTkButton(
        foot, text="Abrir pasta", fg_color="transparent",
        text_color=LINK_BLUE, hover_color=("gray85", "gray25"),
        font=ctk.CTkFont(size=max(7, px - 2), underline=True),
        command=open_cmd, width=80, height=24), "file_link")
    file_link.pack(side="right")
    return row


EMOJIS = (
    "😀😁😂🤣😊😍😎🤔😐😅😭😡"
    "👍👎🙏👏💪🔥🎉✅❌❓❗💯"
    "❤️💔👀👋🤝👨👩👧👦💼📌"
    "📎📁📅⏰💡💰📞✉️⭐🌹☀️"
    "☕🍺🍰🚗✈️🏠⚽🎵🚀🐞✔️"
)


def open_emoji_picker(parent: tk.Misc, entry, cols: int = 12) -> None:
    """Grade de emojis: clica e insere no campo de texto (vale Win+. também)."""
    win = ctk.CTkToplevel(parent)
    win.title("Emojis")
    win.geometry("420x300")
    win.resizable(False, False)
    try:
        center_window(win, None)
    except tk.TclError:
        pass
    try:
        win.grab_set()
    except tk.TclError:
        pass
    grid = ctk.CTkScrollableFrame(win)
    grid.pack(fill="both", expand=True, padx=8, pady=8)
    for i, ch in enumerate(EMOJIS):
        ctk.CTkButton(grid, text=ch, width=36, height=36,
                      fg_color="transparent", text_color=("black", "white"),
                      font=ctk.CTkFont(size=18),
                      command=lambda c=ch: _emoji_pick(win, entry, c)
                      ).grid(row=i // cols, column=i % cols, padx=1, pady=1)
    ctk.CTkButton(win, text="Fechar", width=100,
                  command=win.destroy).pack(pady=(0, 8))


def _emoji_pick(win, entry, ch: str) -> None:
    try:
        entry.insert("insert", ch)
        entry.focus_set()
    except tk.TclError:
        pass


def bubble_clock(direction: str, ts: str, pending: bool = False) -> str:
    """Horário p/ dentro do balão (+ tique de entregue no enviado).

    pending=True (v1.29): mensagem na fila, ainda sem ACK do contato.
    """
    clock = chatview.bubble_time(ts)
    if direction == "out" and clock:
        clock = f"{clock} (pendente)" if pending else f"{clock} ✓"
    return clock


def file_history_text(which: str, name: str, size_bytes: float) -> str:
    """Linha do histórico p/ arquivos: nome completo com extensão."""
    return f"[arquivo {which}] {name} ({chatview.format_size(size_bytes)})"


class ChatWindow:
    """Janela de conversa 1-1 em CustomTkinter (backend inalterado)."""

    def __init__(self, app: "App", ip: str, info: dict):
        self.app = app
        self.ip = ip
        self.win = ctk.CTkToplevel(app.root)
        self.win.geometry(chatview.conversation_geometry(app.settings.chat_geometry))
        self.win.minsize(chatview.MIN_CHAT_WIDTH, chatview.MIN_CHAT_HEIGHT)
        self._refresh_title(info)
        self._apply_icon()
        # barra: status + Convidar + Enviar Arquivo(s) + atalhos
        top = ctk.CTkFrame(self.win, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(4, 0))
        self.status = ctk.CTkLabel(top, text="", text_color="gray", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self._chat_toolbar_button(top, "ℹ", "Informações do contato", "sobre.png",
                                  lambda: self.app.peer_info_dialog(self.ip))
        self._chat_toolbar_button(top, "📁", "Arquivos recebidos", "arquivos.png",
                                  lambda: self.app.open_inbox())
        self._chat_toolbar_button(top, "H", "Histórico desta conversa", "historico.png",
                                  lambda: self.app.open_history(select_peer=self.ip))
        self._chat_toolbar_button(top, "A", "Conectar via AnyDesk", "anydesk.png",
                                  lambda: self.app._remote_connect(self.ip, "anydesk"))
        self._chat_toolbar_button(top, "R", "Conectar via RustDesk", "rustdesk.png",
                                  lambda: self.app._remote_connect(self.ip, "rustdesk"))
        ctk.CTkButton(top, text="Convidar", width=70,
                      command=self.invite_dialog).pack(side="right", padx=2)
        ctk.CTkButton(top, text="Arquivo(s)", width=80,
                      command=self.send_file).pack(side="right", padx=2)
        # mensagem de status em linha própria (não espreme os botões)
        self.status_msg_label = ctk.CTkLabel(
            self.win, text="", anchor="w", justify="left",
            text_color=("black", "white"),
            font=ctk.CTkFont(weight="bold"))
        self.status_msg_label.pack(fill="x", padx=6)
        self.scroll = ctk.CTkScrollableFrame(self.win, fg_color=BUBBLE_LOG_BG)
        self.scroll.pack(fill="both", expand=True, padx=6)
        bind_rewrap(self.win, self.scroll)  # texto proporcional à janela (v1.32)
        # -- barra de resposta (v1.30): aparece ao escolher "Responder" ----
        self._reply: dict | None = None
        self._reply_bar = ctk.CTkFrame(self.win, fg_color=BUBBLE_SEP_BG,
                                       corner_radius=8)
        self._reply_lbl = ctk.CTkLabel(self._reply_bar, text="",
                                       anchor="w", font=ctk.CTkFont(size=11))
        self._reply_lbl.pack(side="left", fill="x", expand=True,
                             padx=(8, 4), pady=(4, 0))
        self._reply_excerpt = ctk.CTkLabel(self._reply_bar, text="",
                                           anchor="w", justify="left",
                                           text_color=BUBBLE_SEP_FG,
                                           font=ctk.CTkFont(size=12))
        self._reply_excerpt.pack(side="left", fill="x", expand=True,
                                 padx=(8, 4), pady=(0, 4))
        ctk.CTkButton(self._reply_bar, text="✕", width=28, height=24,
                      fg_color="transparent",
                      command=self._clear_reply).pack(side="right",
                                                      padx=4, pady=4)
        ctk.CTkLabel(self.win, text="Texto da mensagem:", anchor="w").pack(
            fill="x", padx=6)
        self.entry = ctk.CTkTextbox(self.win, height=80)
        self.entry.pack(fill="x", padx=6, pady=2)
        # Atalhos (tela Atalhos): Enter ou Ctrl+Enter envia, conforme config
        self.entry.bind("<Return>", lambda e: self._on_key("Return"))
        self.entry.bind("<Control-Return>", lambda e: self._on_key("Control-Return"))
        self.entry.bind("<Control-v>", self._on_paste, add="+")
        self.entry.bind("<Control-V>", self._on_paste, add="+")
        self.focused = False
        self.win.bind("<FocusIn>", lambda e: setattr(self, "focused", True))
        self.win.bind("<FocusOut>", lambda e: setattr(self, "focused", False))
        self.win.bind("<Button-1>", self._focus_from_click, add="+")
        bot = ctk.CTkFrame(self.win, fg_color="transparent")
        bot.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(bot, text="Fechar", width=100,
                      command=self.win.destroy).pack(side="right")
        ctk.CTkButton(bot, text="Enviar", width=100,
                      command=self.send).pack(side="right", padx=4)
        ctk.CTkButton(bot, text="😊", width=36,
                      command=lambda: open_emoji_picker(self.win, self.entry)).pack(
                          side="right", padx=4)
        # histórico recente (tela Mensagens: "Exibir mensagens recentes")
        # carimbo sempre visível no balão (HH:MM:SS)
        self._last_date = ""
        self._pending: dict[str, object] = {}      # mid -> linha do balão
        self._pending_ts: dict[str, str] = {}
        if app.settings.show_recent:
            pend = app.store.pending_ids(ip)
            reps = app.store.replies_with(ip)
            for mid, direction, text, ts in app.store.messages_with_ids(ip):
                self._dated(direction, text, ts, mid=mid, pending=mid in pend,
                            reply=reps.get(mid))
            scroll_end(self.scroll)
        self._sys(f"--- conversa com {roster.label_of(info)}@{ip} ---")
        self.apply_font()
        self._enable_drop()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        esc_closes(self.win, self._on_close)
        self.entry.focus_set()
        self.update_status_line(info)
        # centraliza DEPOIS do conteúdo + ao mapear (tamanho real) e
        # rola p/ a última mensagem
        center_soon(self.win)
        scroll_end(self.scroll)

    def _chat_toolbar_button(self, parent, text: str, tip: str, icon: str, cmd) -> None:
        img = self.app._load_icon(icon, 18)
        if img is not None:
            b = ctk.CTkButton(parent, image=img, text="", width=28, height=28,
                              fg_color="transparent", command=cmd)
        else:
            b = ctk.CTkButton(parent, text=text, width=28, height=28, command=cmd)
        b.pack(side="right", padx=1)
        _tooltip(b, tip)

    def apply_font(self) -> None:
        """Tamanho da fonte (tela Mensagens)."""
        px = chatview.font_px(self.app.settings.font_size)
        try:
            self.entry.configure(font=ctk.CTkFont(size=px))
            self._reply_lbl.configure(
                font=ctk.CTkFont(size=max(8, px - 2), weight="bold"))
            self._reply_excerpt.configure(font=ctk.CTkFont(size=px))
            apply_chat_fonts(self.scroll, px)
            scroll_end(self.scroll)
        except tk.TclError:
            pass

    def _refresh_title(self, info: dict) -> None:
        self.win.title(f"{roster.label_of(info)} - Conversa")

    def _apply_icon(self) -> None:
        """Ícone Conversa nas janelas de conversa (PNG via iconphoto)."""
        try:
            from PIL import Image, ImageTk
            path = config.asset_path("conversa.png")
            if not path:
                return
            photo = ImageTk.PhotoImage(Image.open(path).convert("RGBA").resize((16, 16)))
            self.win.iconphoto(True, photo)
            self._chat_icon = photo  # evita GC
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            self.app.settings.chat_geometry = self.win.geometry()
            profile.save(self.app.profile, self.app.settings)
        except (tk.TclError, OSError):
            pass
        self.app.chat_windows.pop(self.ip, None)
        self.win.destroy()

    # -- renderização (só visual; dados e ordem preservados) -------------
    def _sys(self, line: str) -> None:
        px = chatview.font_px(self.app.settings.font_size)
        lbl = _chat_role(ctk.CTkLabel(
            self.scroll, text=line, text_color="gray",
            font=ctk.CTkFont(size=max(8, px - 2))), "system")
        lbl.pack(pady=2)

    def _dated(self, direction: str, text: str, ts: str, name: str = "",
               mid: str = "", pending: bool = False,
               reply: dict | None = None) -> None:
        show_pill = ts and self.app.settings.show_datetime
        label = chatview.date_label(ts) if show_pill else ""
        px = chatview.font_px(self.app.settings.font_size)
        if label and label != self._last_date:
            build_date_pill(self.scroll, label, px)
            self._last_date = label
        row = build_bubble(self.scroll, direction, text,
                           bubble_clock(direction, ts, pending=pending),
                           name=name, reply=reply, font_px=px)
        if pending and mid:
            self._pending[mid] = row
            self._pending_ts[mid] = ts
        if mid:
            try:
                row._mid = mid  # v1.30: botão direito cita este balão
            except Exception:
                pass
            self._bind_bubble_menu(row, direction, text, name)
        scroll_end(self.scroll)

    def _bind_bubble_menu(self, row, direction: str, text: str,
                          name: str) -> None:
        """Balão: botão direito → menu; duplo-clique → Responder (v1.31)."""
        stack = [row]
        while stack:
            w = stack.pop()
            try:
                w.bind("<Button-3>",
                       lambda e, r=row, d=direction, t=text, n=name:
                       self._bubble_menu(e, r, d, t, n), add="+")
                w.bind("<Double-Button-1>",
                       lambda e, r=row, d=direction, t=text, n=name:
                       self._bubble_dblclick(e, r, d, t, n), add="+")
            except tk.TclError:
                continue
            try:
                stack.extend(w.winfo_children())
            except tk.TclError:
                pass

    def _bubble_dblclick(self, event, row, direction: str, text: str,
                         name: str) -> None:
        """Duplo-clique no balão inicia a resposta (atalho do WhatsApp)."""
        mid = getattr(row, "_mid", "")
        if not mid or not text:
            return
        if direction == "in":
            who = name or self.app.peer_label(self.ip)
        else:
            who = name or self.app.profile.effective_display()
        self._start_reply(mid, who, text)

    def _bubble_menu(self, event, row, direction: str, text: str,
                     name: str) -> None:
        mid = getattr(row, "_mid", "")
        if not mid:
            return
        if direction == "in":
            who = name or self.app.peer_label(self.ip)
        else:
            who = name or self.app.profile.effective_display()
        m = tk.Menu(self.win, tearoff=0)
        m.add_command(label="Responder",
                      command=lambda: self._start_reply(mid, who, text))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                m.grab_release()
            except tk.TclError:
                pass

    def _start_reply(self, mid: str, who: str, text: str) -> None:
        """Mostra a prévia da resposta acima do campo de texto."""
        self._reply = {"id": mid, "name": str(who)[:80],
                       "text": str(text)[:300]}
        try:
            self._reply_lbl.configure(text=f"Respondendo a {who}")
            self._reply_excerpt.configure(text=str(text)[:300])
            self._reply_bar.pack(fill="x", padx=6, pady=(2, 0),
                                 before=self.entry)
            self.entry.focus_set()
        except (tk.TclError, AttributeError):
            pass

    def _clear_reply(self) -> None:
        """Cancela a resposta pendente (✕ na barra)."""
        self._reply = None
        try:
            self._reply_bar.pack_forget()
        except tk.TclError:
            pass

    def mark_delivered(self, mid: str) -> None:
        """Fila entregou: troca "(pendente)" pelo tique (v1.29)."""
        row = self._pending.pop(mid, None)
        ts = self._pending_ts.pop(mid, "")
        if row is None:
            return
        lbl = getattr(row, "_clock_label", None)
        try:
            if lbl is not None:
                lbl.configure(text=bubble_clock("out", ts))
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            log_crash("mark_delivered", e)

    def _append(self, line: str, at_bottom: bool = True) -> None:
        self._sys(line)
        if at_bottom:
            scroll_end(self.scroll)

    def _append_file_line(self, name: str, size_kb: float, path: str,
                          direction: str = "in") -> None:
        """Cartão tamanho de balão: selo + nome + hora + Abrir pasta."""
        clock = chatview.bubble_time(time.strftime("%d/%m/%Y - %H:%M:%S"))
        px = chatview.font_px(self.app.settings.font_size)
        build_file_card(self.scroll, name, clock, direction,
                        lambda p=path: self._open_containing(p), px)
        scroll_end(self.scroll)

    def incoming(self, text: str, info: dict, mid: str = "",
                 reply: dict | None = None) -> None:
        self._refresh_title(info)
        s = self.app.settings
        ts = time.strftime("%d/%m/%Y - %H:%M:%S")  # sempre: identifica a hora
        self._dated("in", text, ts, mid=mid, reply=reply)
        self.update_status_line(info)
        self.win.after(0, self._announce)
        self.win.after(0, self._focus_entry)

    def _focus_entry(self) -> None:
        """Foco no campo de texto (nunca derruba se a janela fechou)."""
        try:
            self.entry.focus()
            self.entry.focus_set()
            if hasattr(self.entry, "_textbox"):
                self.entry._textbox.focus_set()
        except tk.TclError:
            pass
        except Exception as e:
            log_crash("chat_focus", e)

    def _focus_from_click(self, event) -> None:
        """Clique em área não interativa da conversa leva foco à digitação."""
        widget = getattr(event, "widget", None)
        blocked = (ctk.CTkButton, ctk.CTkEntry, ctk.CTkTextbox,
                   ctk.CTkScrollbar, tk.Button, tk.Entry, tk.Text)
        while widget is not None and widget is not self.win:
            if isinstance(widget, blocked):
                return
            widget = getattr(widget, "master", None)
        try:
            self.win.after(0, self._focus_entry)
        except tk.TclError:
            pass

    def update_status_line(self, info: dict) -> None:
        """Curta em cima ('está ausente'); mensagem em negrito embaixo."""
        name = roster.label_of(info)
        st = str(info.get("status", "online"))
        word = {"online": "disponível", "busy": "ocupado",
                "away": "ausente"}.get(st, st)
        msg = str(info.get("status_msg", "") or "")
        try:
            self.status.configure(text=f"{name} está {word}")
            self.status_msg_label.configure(text=msg)
        except tk.TclError:
            pass

    def _announce(self) -> None:
        """Sempre traz à frente + pisca se sem foco (novas mensagens)."""
        try:
            self._activate_chat_window(self)
        except Exception:
            pass
        if not self.focused:
            flash_window(self.win)

    def _on_key(self, key: str) -> str | None:
        if send_binding_allows(key, self.app.settings.send_key):
            self.send()
            return "break"
        return None

    def _on_paste(self, _event=None) -> str | None:
        """Ctrl+V: se houver print/imagem na área de transferência, envia como PNG."""
        try:
            from PIL import ImageGrab, Image
            data = ImageGrab.grabclipboard()
            if isinstance(data, Image.Image):
                folder = Path(config.APP_DATA) / "clipboard"
                folder.mkdir(parents=True, exist_ok=True)
                fpath = folder / f"print_{time.strftime('%Y%m%d_%H%M%S')}.png"
                data.save(fpath, "PNG")
                self.send_files([str(fpath)])
                return "break"
        except Exception:
            return None
        return None

    def send(self) -> None:
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return
        text = chatview.translate_emoticons(text)
        info = self.app.selected_info(self.ip)
        reply = self._reply
        self.entry.delete("1.0", "end")
        self.app.touch()
        offline = str(info.get("status", "online")) == "offline"
        # v1.37: salva/exibe na hora; socket + ACK ficam no worker da fila.
        # ENTER nunca espera ping, conexão TCP ou timeout na thread da UI.
        self.app.queue_outgoing(self.ip, text, reply=reply, offline=offline)

    def invite_dialog(self) -> None:
        """Convidar: envia convite a outro usuário e abre a conversa com ele."""
        peers = {ip: i for ip, i in self.app.disc.get_roster().items()
                 if ip != self.ip and i.get("status") != "offline"}
        if not peers:
            messagebox.showinfo("Convidar", "Nenhum outro usuário online.", parent=self.win)
            return
        win = ctk_dialog(self.win, "Convidar para a conversa", "320x360")
        box = ctk.CTkScrollableFrame(win)
        box.pack(fill="both", expand=True, padx=8, pady=8)
        ids = sorted(peers, key=lambda ip: roster.label_of(peers[ip]).lower())
        sel = {"ip": ""}

        def choose(ip: str) -> None:
            sel["ip"] = ip
            for child in box.winfo_children():
                try:
                    if isinstance(child, ctk.CTkButton):
                        child.configure(fg_color="transparent")
                except tk.TclError:
                    pass
            for child in box.winfo_children():
                try:
                    if isinstance(child, ctk.CTkButton) and child.cget("text") == roster.label_of(peers[ip]):
                        child.configure(fg_color=("gray75", "gray30"))
                except tk.TclError:
                    pass

        for ip in ids:
            ctk.CTkButton(box, text=roster.label_of(peers[ip]), anchor="w",
                          fg_color="transparent", text_color=("black", "white"),
                          command=lambda i=ip: choose(i)).pack(fill="x", pady=1)

        def ok() -> None:
            ip = sel["ip"]
            if not ip:
                return
            text = chatview.invite_text(self.app.profile.effective_display())
            try:
                mid = chat.send_message(ip, text,
                                        from_name=self.app.profile.effective_display(),
                                        from_user=config.my_user(), key=self.app.key)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Falha", str(e), parent=win)
                return
            self.app.store.add_message(mid, ip, "out", text)
            logger.log_message(self.app.settings, self.app.peer_label(ip), "out", text)
            win.destroy()
            self.app.open_chat(ip)

        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bot, text="Cancelar", width=100,
                      command=win.destroy).pack(side="right")
        ctk.CTkButton(bot, text="Convidar", width=100,
                      command=ok).pack(side="right", padx=4)

    def send_file(self) -> None:
        fpaths = filedialog.askopenfilenames(parent=self.win)
        if not fpaths:
            return
        self.send_files(list(fpaths))

    def send_files(self, fpaths: list[str]) -> None:
        """Envio em thread com barra de progresso + Cancelar (estilo clássico)."""
        if getattr(self, "_sending", False):
            messagebox.showinfo("Arquivos", "Já há um envio em andamento.", parent=self.win)
            return
        self._sending = True
        self._cancel_send = False
        total_all = len(fpaths)
        self._xfer_show(mode="send")

        def progress(name: str, done: int, total: int):
            if self._cancel_send:
                return False
            left_kb = (total - done) // 1024
            self.app._ui_call(self._xfer_progress,
                              f"Enviando {name} ({done // 1024}/{total // 1024} KB, "
                              f"{left_kb} KB restantes...)", done, total)
            return True

        def run() -> None:
            try:
                for i, fpath in enumerate(fpaths, 1):
                    if self._cancel_send:
                        break
                    p = Path(fpath)
                    self.app._ui_call(self._xfer_status,
                                      f"Enviando {i} arquivo(s); {total_all - i} restante(s)")
                    files.send_file(self.ip, fpath,
                                    from_name=self.app.profile.effective_display(),
                                    key=self.app.key, on_progress=progress)
                    size_kb = p.stat().st_size / 1024
                    self.app._ui_call(self._xfer_done,
                                      f"{i} arquivo(s) ({size_kb:,.0f} KB) enviado(s)".replace(",", "."),
                                      str(fpath))
                    self.app._ui_call(self._append_file_line, p.name, size_kb,
                                      str(fpath), "out")
                    self.app.store.add_message(
                        f"file-out-{time.time_ns()}-{self.ip}", self.ip, "out",
                        file_history_text("enviado", p.name, p.stat().st_size))
                    logger.log_file_event(self.app.settings, self.app.peer_label(self.ip),
                                          "out", p.name)
            except Exception as e:  # noqa: BLE001 - mostra erro na tela
                self.app._ui_call(messagebox.showerror, "Falha", str(e))
                self.app._ui_call(self._xfer_hide)
            finally:
                self._sending = False
        threading.Thread(target=run, daemon=True).start()

    def send_one_file(self, fpath: str) -> None:
        self.send_files([fpath])

    # -- barra de transferência (progresso + Abrir pasta/Cancelar) --------
    def _xfer_show(self, mode: str) -> None:
        if not hasattr(self, "_xfer"):
            fr = ctk.CTkFrame(self.win)
            fr.pack(fill="x", padx=6, pady=2)
            self._xfer_label = ctk.CTkLabel(fr, anchor="w", text="")
            self._xfer_label.pack(fill="x")
            self._xfer_bar = ctk.CTkProgressBar(fr)
            self._xfer_bar.pack(fill="x", pady=2)
            self._xfer_bar.set(0)
            brow = ctk.CTkFrame(fr, fg_color="transparent")
            brow.pack(fill="x")
            self._xfer_link = ctk.CTkButton(brow, text="", width=100,
                                            fg_color="transparent",
                                            text_color=LINK_BLUE)
            self._xfer_link.pack(side="right")
            self._xfer = fr
        else:
            self._xfer.pack(fill="x", padx=6, pady=2)
        self._xfer_mode = mode
        if mode == "send":
            self._xfer_link.configure(text="Cancelar", command=self._xfer_cancel)
        self._xfer_bar.set(0)
        self._xfer_label.configure(text="")

    def _xfer_hide(self) -> None:
        if hasattr(self, "_xfer"):
            self._xfer.pack_forget()

    def _xfer_cancel(self) -> None:
        self._cancel_send = True

    def _xfer_status(self, text: str) -> None:
        self._xfer_show(getattr(self, "_xfer_mode", "send"))
        self._xfer_label.configure(text=text)

    def _xfer_progress(self, text: str, done: int, total: int) -> None:
        self._xfer_show("send")
        self._xfer_label.configure(text=text)
        try:
            self._xfer_bar.set((done / total) if total else 0)
        except tk.TclError:
            pass

    def _xfer_done(self, text: str, fpath: str = "") -> None:
        self._xfer_show(getattr(self, "_xfer_mode", "send"))
        self._xfer_label.configure(text=text + " - Completo")
        try:
            self._xfer_bar.set(1.0)
        except tk.TclError:
            pass
        if fpath:
            self._xfer_link.configure(text="Abrir pasta",
                                      command=lambda: self._open_containing(fpath))
        else:
            self._xfer_link.configure(text="", command=lambda: None)

    @staticmethod
    def _open_containing(fpath: str) -> None:
        """Abre o Explorer na pasta onde está o arquivo recebido/enviado."""
        try:
            p = Path(fpath)
            folder = p if p.is_dir() else p.parent
            if not folder.exists():
                folder = Path(config.APP_DATA) / "inbox"
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except OSError:
            try:
                os.startfile(str(Path(fpath).parent))  # type: ignore[attr-defined]
            except OSError:
                pass

    # -- arrastar e soltar (drop de arquivos na conversa) ------------------
    def _enable_drop(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            return  # sem tkdnd: botão Enviar Arquivo(s) continua valendo
        try:
            self.entry.drop_target_register(DND_FILES)
            self.entry.dnd_bind("<<Drop>>", self._on_drop)
        except tk.TclError:
            pass

    def _on_drop(self, event) -> None:
        try:
            paths = [p for p in self.win.tk.splitlist(event.data)
                     if Path(p).is_file()]
        except tk.TclError:
            return
        if paths:
            self.send_files(paths)


class GroupChatWindow:
    """Start Group Conversation: fan-out p/ membros + log do grupo."""

    def __init__(self, app: "App", dept: str):
        self.app = app
        self.dept = dept
        self._last_date = ""
        self.win = ctk.CTkToplevel(app.root)
        self.win.geometry(chatview.DEFAULT_CHAT_GEOMETRY)
        self.win.minsize(chatview.MIN_CHAT_WIDTH, chatview.MIN_CHAT_HEIGHT)
        self.win.title(f"{dept} - Conversa em Grupo")
        esc_closes(self.win, self._on_close)
        self.scroll = ctk.CTkScrollableFrame(self.win, fg_color=BUBBLE_LOG_BG)
        self.scroll.pack(fill="both", expand=True, padx=6, pady=4)
        bind_rewrap(self.win, self.scroll)  # texto proporcional à janela (v1.32)
        self._sys(f"--- conversa em grupo: {dept} ---")
        ctk.CTkLabel(self.win, text="Texto da mensagem (@nome menciona):",
                     anchor="w").pack(fill="x", padx=6)
        self.entry = ctk.CTkTextbox(self.win, height=80)
        self.entry.pack(fill="x", padx=6, pady=2)
        self.entry.bind("<Return>", lambda e: self._on_key("Return"))
        self.entry.bind("<Control-Return>", lambda e: self._on_key("Control-Return"))
        bot = ctk.CTkFrame(self.win, fg_color="transparent")
        bot.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(bot, text="Fechar", width=100,
                      command=self._on_close).pack(side="right")
        ctk.CTkButton(bot, text="Enviar", width=100,
                      command=self.send).pack(side="right", padx=4)
        ctk.CTkButton(bot, text="😊", width=36,
                      command=lambda: open_emoji_picker(self.win, self.entry)).pack(
                          side="right", padx=4)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.entry.focus_set()
        self.apply_font()
        center_soon(self.win)
        scroll_end(self.scroll)

    def _on_close(self) -> None:
        self.app.group_windows.pop(self.dept, None)
        self.win.destroy()

    def apply_font(self) -> None:
        """Tamanho da fonte (tela Mensagens)."""
        px = chatview.font_px(self.app.settings.font_size)
        try:
            self.entry.configure(font=ctk.CTkFont(size=px))
            apply_chat_fonts(self.scroll, px)
            scroll_end(self.scroll)
        except tk.TclError:
            pass

    def _sys(self, line: str) -> None:
        px = chatview.font_px(self.app.settings.font_size)
        lbl = _chat_role(ctk.CTkLabel(
            self.scroll, text=line, text_color="gray",
            font=ctk.CTkFont(size=max(8, px - 2))), "system")
        lbl.pack(pady=2)

    def _append(self, line: str) -> None:
        self._sys(line)
        scroll_end(self.scroll)

    def members(self) -> list[str]:
        groups = roster.group_peers(self.app.disc.get_roster(), hide_offline=True,
                                    aliases=self.app.settings.group_aliases,
                                    hidden=self.app.settings.hidden_groups,
                                    overrides=self.app.settings.peer_groups,
                                    custom=self.app.settings.custom_groups)
        return [ip for ip, _ in groups.get(self.dept, [])]

    def _on_key(self, key: str) -> str | None:
        if send_binding_allows(key, self.app.settings.send_key):
            self.send()
            return "break"
        return None

    def _dated(self, direction: str, text: str, ts: str, name: str = "",
               mention: bool = False) -> None:
        show_pill = ts and self.app.settings.show_datetime
        label = chatview.date_label(ts) if show_pill else ""
        px = chatview.font_px(self.app.settings.font_size)
        if label and label != self._last_date:
            build_date_pill(self.scroll, label, px)
            self._last_date = label
        build_bubble(self.scroll, direction, text,
                     bubble_clock(direction, ts), name=name, mention=mention,
                     font_px=px)
        scroll_end(self.scroll)

    def send(self) -> None:
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return
        text = chatview.translate_emoticons(text)
        ips = self.members()
        if not ips:
            messagebox.showinfo("Grupo", f"Nenhum membro online em '{self.dept}'.", parent=self.win)
            return
        res = chat.send_broadcast(ips, text, from_name=self.app.profile.effective_display(),
                                  from_user=config.my_user(), key=self.app.key)
        ok = sum(1 for v in res.values() if v == "ok")
        for ip, st in res.items():
            if st == "ok":
                self.app.store.add_message(f"grp-{time.time()}-{ip}", ip, "out", text)
        self._append(f"[eu -> {self.dept} ({ok}/{len(ips)})]")
        ts = time.strftime("%d/%m/%Y - %H:%M:%S")  # sempre: identifica a hora
        self._dated("out", text, ts)
        self.entry.delete("1.0", "end")
        self.app.touch()

    def incoming(self, ip: str, info: dict, text: str,
                 mention: bool = False) -> None:
        ts = time.strftime("%d/%m/%Y - %H:%M:%S")  # sempre: identifica a hora
        self._dated("in", text, ts, name=roster.label_of(info),
                    mention=mention)
        self.win.after(0, self._announce)

    def _announce(self) -> None:
        try:
            self.win.lift()
        except tk.TclError:
            pass
        except Exception as e:  # janela fechando durante o after(0)
            log_crash("group_announce", e)
            return
        flash_window(self.win)

class App:
    def __init__(self, root):
        self.root = root
        self._lock = single_instance.acquire()
        if self._lock is None:
            messagebox.showinfo(
                "LAN Messenger",
                "O LAN Messenger já está em execução.\n"
                "Procure o ícone verde na bandeja do sistema.")
            raise SystemExit(0)
        self.profile, self.settings = profile.load()
        self.store = Store()
        self.hw_info = sysinfo.computer_info()
        self.disc = discovery.Discovery(
            name=config.my_hostname(), user=config.my_user(),
            display=self.profile.effective_display(),
            dept=self.profile.department, role=self.profile.role,
            anydesk=self.profile.anydesk_id,
            rustdesk=self.profile.rustdesk_id,
            hw=self.hw_info).start()
        if self.profile.anydesk_id or self.profile.rustdesk_id:
            pass  # já preenchidos
        threading.Thread(target=self._autodetect_ids, daemon=True).start()
        self.key = crypto.get_key(self.settings)
        self.chat_server = chat.ChatServer(on_message=self.on_msg_threadsafe,
                                           key=self.key,
                                           on_hello=self.disc.local_beacon).start()
        self.file_server = files.FileServer(
            inbox=self.settings.inbox_dir, on_file=self.on_file_threadsafe,
            on_request=self._file_request, key=self.key).start()
        self._file_asks: queue.Queue = queue.Queue()  # (header, sender, result-box, event)
        self._ui_queue: queue.Queue = queue.Queue()  # (fn, args) p/ main thread
        self.tray: tray_mod.TrayController | None = None
        self._tray_cmds: queue.Queue = queue.Queue()
        self._in_tray = False
        self._really_quit = False
        self._flushing = False        # flush da fila em andamento
        self._flush_scheduled = False  # flush já agendado no after
        self._flush_again = False     # nova mensagem chegou durante o flush
        self.chat_windows: dict[str, ChatWindow] = {}
        self.group_windows: dict[str, GroupChatWindow] = {}
        self._collapsed_groups: set[str] = set()
        self._seen_online: set[str] | None = None  # None = primeira carga (sem som)
        self._roster_sig: tuple = ()
        self._refresh_count: int = 0
        self._manual_status = False
        self._status_buttons: dict[str, object] = {}
        self._selected_ip: str = ""
        self._selected_group: str = ""
        self._item_ip: dict = {}     # widget -> ip (compat)
        self._item_group: dict = {}  # widget -> grupo (compat)
        self._last_active = time.time()
        self._bring_event: str | None = None
        self._build()
        self._ensure_tray()
        self.refresh()
        self._recover_peers_async()
        self.root.after(10000, self._tcp_presence_tick)
        self._apply_bring_hotkey()
        self.root.after(3000, self._auto_refresh)
        self.root.after(30000, self._away_check)
        self.root.after(250, self._pump_file_asks)
        self.root.after(250, self._pump_tray_cmds)
        self.root.after(100, self._pump_ui)
        self.root.after(4000, self._outbox_tick)
        root.bind_all("<KeyPress>", lambda e: self.touch(), add="+")
        root.bind_all("<ButtonPress>", lambda e: self.touch(), add="+")
        esc_closes(root, self._on_esc_main)
        root.protocol("WM_DELETE_WINDOW", self._on_quit)
        root.bind("<F2>", self._on_tree_key, add="+")
        root.bind("<Delete>", self._on_tree_key, add="+")
        root.bind("<Return>", self._on_tree_key, add="+")
        root.bind("<Control-Up>", self._on_tree_key, add="+")
        root.bind("<Control-Down>", self._on_tree_key, add="+")
        self._install_crash_reporter()
        threading.Thread(target=self._check_update_worker, daemon=True,
                         name="update-check").start()

    def _install_crash_reporter(self) -> None:
        """Erros em callbacks Tk (after, bindings) vão para logs/crash.log.

        Substitui o diálogo modal "Application Error" (que não mostra o
        traceback útil) por registro em arquivo + aviso na statusbar.
        """
        def report(_tp, exc, _tb) -> None:
            path = log_crash("callback Tk", exc)
            try:
                self.statusbar.configure(text=f"Erro interno registrado em {path}")
            except Exception:
                pass
        self.root.report_callback_exception = report

    def _check_update_worker(self) -> None:
        """Consulta GitHub fora da UI; sem internet não mostra erro."""
        result = updates.check_latest(config.APP_VERSION)
        if result is not None and not self._really_quit:
            self._ui_call(self._offer_update, *result)

    def _offer_update(self, version: str, url: str) -> None:
        """Avisa e leva o usuário à página oficial de Releases."""
        try:
            self.statusbar.configure(
                text=f"Nova versão {version} disponível para download.")
            open_now = messagebox.askyesno(
                "Nova versão disponível",
                f"A versão {version} do LAN Messenger está disponível.\n\n"
                "Deseja abrir a página de Releases para baixar?",
                parent=self.root)
        except tk.TclError:
            return
        if open_now:
            open_url(url)

    # -- fila de saída: mensagem para contato offline (v1.29) ------------
    def queue_outgoing(self, ip: str, text: str,
                       reply: dict | None = None,
                       offline: bool = True) -> None:
        """Exibe e guarda imediatamente; entrega TCP ocorre no worker."""
        mid = uuid.uuid4().hex
        try:
            self.store.add_message(mid, ip, "out", text)
            self.store.queue_message(mid, ip, text)
            if reply:
                self.store.set_reply(mid, str(reply.get("id", "")),
                                     str(reply.get("name", ""))[:80],
                                     str(reply.get("text", ""))[:300])
        except Exception as e:
            log_crash("outbox_queue", e)
            return
        logger.log_message(self.settings, self.peer_label(ip), "out", text)
        ts = time.strftime("%d/%m/%Y - %H:%M:%S")
        win = self.chat_windows.get(ip)
        if win is not None:
            win._dated("out", text, ts, mid=mid, pending=True, reply=reply)
            win._clear_reply()
        try:
            if offline:
                status = (f"Mensagem guardada para {self.peer_label(ip)} — "
                          "sai sozinha quando ele ficar online.")
            else:
                status = f"Enviando mensagem para {self.peer_label(ip)}..."
            self.statusbar.configure(text=status)
        except tk.TclError:
            pass
        self.flush_outbox_soon()

    def flush_outbox_soon(self) -> None:
        """Agenda um flush (curto) sem empilhar vários no after."""
        if self._flush_scheduled or self._really_quit:
            return
        self._flush_scheduled = True
        try:
            self.root.after(20, self._flush_outbox)
        except (tk.TclError, RuntimeError):
            self._flush_scheduled = False

    def _peer_online(self, ip: str) -> bool:
        """Só tenta entregar se o contato aparece online na lista."""
        try:
            info = self.disc.get_roster().get(ip)
        except Exception:
            return False
        return bool(info) and str(info.get("status", "online")) != "offline"

    def _send_queued(self, ip: str, text: str, mid: str) -> None:
        """Envio da fila: mesmo id do banco (balão vira tique ao entregar)."""
        reply = self.store.get_reply(mid)
        chat.send_message(ip, text,
                          from_name=self.profile.effective_display(),
                          from_user=config.my_user(), key=self.key, msg_id=mid,
                          reply=reply)

    def _flush_outbox(self) -> None:
        """Dispara o flush em thread (socket nunca na thread da UI)."""
        self._flush_scheduled = False
        if self._flushing or self._really_quit:
            if self._flushing:
                self._flush_again = True
            return
        self._flushing = True

        def done(mid: str, ip: str, _text: str) -> None:
            self._ui_call(self._queued_delivered, mid, ip)

        def run() -> None:
            try:
                flush_outbox(self.store, self._peer_online, self._send_queued, done)
            finally:
                self._flushing = False
                if self._flush_again:
                    self._flush_again = False
                    self._ui_call(self.flush_outbox_soon)

        try:
            threading.Thread(target=run, daemon=True, name="outbox").start()
        except Exception as e:
            self._flushing = False
            log_crash("outbox_thread", e)

    def _queued_delivered(self, mid: str, ip: str) -> None:
        """Main thread: fila entregou (troca o balão e avisa no rodapé)."""
        win = self.chat_windows.get(ip)
        if win is not None:
            win.mark_delivered(mid)
        try:
            self.statusbar.configure(
                text=f"Mensagem entregue a {self.peer_label(ip)}.")
        except tk.TclError:
            pass

    def _outbox_tick(self) -> None:
        """Retenta a fila a cada 10s enquanto o app estiver aberto."""
        self._flush_outbox()
        if not self._really_quit:
            try:
                self.root.after(10000, self._outbox_tick)
            except (tk.TclError, RuntimeError):
                pass

    def _on_esc_main(self) -> None:
        """ESC na principal minimiza (bandeja, ou barra se configurado)."""
        if tray_mod is not None and tray_mod.HAVE_TRAY:
            self.hide_to_tray()
        else:
            self.root.iconify()

    # -- construção --------------------------------------------------
    def _build(self) -> None:
        self.root.title(config.APP_NAME)
        if chatview.valid_geometry(self.settings.main_geometry):
            self.root.geometry(self.settings.main_geometry)
        else:
            self.root.geometry("320x640")
        ico = config.asset_path("app.ico")
        if ico:
            try:
                self.root.iconbitmap(ico)
            except tk.TclError:
                pass
        # atalhos da janela principal (estilo clássico; ícones em assets/)
        bar = ctk.CTkFrame(self.root, fg_color="transparent")
        bar.pack(fill="x", padx=2, pady=2)
        self._icons: dict[str, object] = {}
        for emoji, tip, cmd, icon in TOOLBAR_BUTTONS:
            self._tip(emoji, tip, getattr(self, cmd), bar, icon)
        self.roster_box = ctk.CTkScrollableFrame(self.root)
        self.roster_box.pack(fill="both", expand=True, padx=4, pady=2)
        self.roster_box.bind("<Button-3>", self._bg_popup, add="+")
        self.root.bind("<Button-3>", self._bg_popup, add="+")
        foot = ctk.CTkFrame(self.root, fg_color="transparent")
        foot.pack(fill="x", padx=4, pady=(2, 0))
        foot.columnconfigure(0, weight=1)
        self._status_buttons = {}
        for col, (st, label) in enumerate((
                ("online", "● Disponível"),
                ("busy", "● Ocupado"),
                ("away", "● Ausente"))):
            b = ctk.CTkButton(foot, text=label, fg_color=STATUS_COLORS[st],
                              text_color=("black", "white"),
                              command=lambda s=st: self.status_button(s))
            b.grid(row=0, column=col, sticky="ew", padx=1)
            foot.columnconfigure(col, weight=1, uniform="status")
            self._status_buttons[st] = b
        self.statusbar = ctk.CTkLabel(self.root, anchor="w", text="",
                                      text_color="gray")
        self.statusbar.pack(fill="x")
        self._item_ip = {}
        self._item_group = {}

    def _apply_key(self) -> None:
        """Recarrega a PSK e propaga aos servidores (sem reiniciar)."""
        self.key = crypto.get_key(self.settings)
        self.chat_server.key = self.key
        self.file_server.key = self.key
        self.refresh()

    def _apply_bring_hotkey(self) -> None:
        """Atalho que traz a janela principal p/ frente (tela Atalhos)."""
        if self._bring_event:
            try:
                self.root.unbind_all(self._bring_event)
            except tk.TclError:
                pass
            self._bring_event = None
        ev = sfx.parse_hotkey(self.settings.bring_hotkey)
        if ev:
            try:
                self.root.bind_all(ev, lambda e: (self.root.lift(), self.root.focus_force()), add="+")
                self._bring_event = ev
            except tk.TclError:
                pass

    def _tip(self, emoji: str, tip: str, cmd, bar, icon: str | None = None) -> None:
        img = self._load_icon(icon, 22) if icon else None
        if img is not None:
            b = ctk.CTkButton(bar, image=img, text="", width=32, height=32,
                              fg_color="transparent", command=cmd)
        else:
            b = ctk.CTkButton(bar, text=emoji, width=32, height=32, command=cmd)
        b.pack(side="left", padx=1)
        _tooltip(b, tip)
        b.bind("<Enter>", lambda _e: self.statusbar.configure(text=tip), add="+")
        b.bind("<Leave>", lambda _e: self.statusbar.configure(text=""), add="+")

    def _load_icon(self, name: str, size: int):
        """PNG de assets/ redimensionado e cacheado (CTkImage)."""
        key = f"{name}@{size}"
        if key in self._icons:
            return self._icons[key]
        try:
            from PIL import Image
            path = config.asset_path(name)
            if not path:
                return None
            photo = ctk.CTkImage(Image.open(path).convert("RGBA"),
                                 size=(size, size))
        except Exception:
            return None
        self._icons[key] = photo
        return photo

    def open_inbox(self) -> None:
        """Mostrar Arquivos Recebidos: abre a pasta de entrada no Explorer."""
        inbox = Path(self.settings.inbox_dir)
        inbox.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(inbox))  # type: ignore[attr-defined]  # Windows
        except OSError as e:
            messagebox.showerror("Arquivos recebidos", str(e), parent=self.root)

    def _open_crash_folder(self) -> None:
        """Abre a pasta do log de erros (logs/crash.log) no Explorer."""
        folder = CRASH_LOG.parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))  # type: ignore[attr-defined]  # Windows
        except OSError as e:
            messagebox.showerror("Log de erros", str(e), parent=self.root)

    def _remember_tree_state(self, _e=None) -> None:
        """Compat: estado de grupos recolhidos já vive em _collapsed_groups."""

    def _toggle_group(self, dept: str) -> None:
        if dept in self._collapsed_groups:
            self._collapsed_groups.discard(dept)
        else:
            self._collapsed_groups.add(dept)
        self._roster_sig = ()
        self.refresh()

    # -- presença / inatividade (tela Geral) --------------------------
    def touch(self) -> None:
        self._last_active = time.time()
        if not self._manual_status and self.disc.status == "away":
            self.disc.set_status("online")

    def _away_check(self) -> None:
        idle_min = (time.time() - self._last_active) / 60
        if (not self._manual_status and idle_min >= self.settings.away_after_min
                and self.disc.status == "online"):
            self.disc.set_status("away")
        self.root.after(30000, self._away_check)

    def _on_quit(self) -> None:
        """Fechar vai p/ bandeja (comportamento clássico); Sair no tray encerra."""
        if tray_mod is not None and tray_mod.HAVE_TRAY and not self._really_quit:
            self.hide_to_tray()
            return
        self.shutdown()

    def _save_main_geometry(self) -> None:
        try:
            self.settings.main_geometry = self.root.geometry()
            profile.save(self.profile, self.settings)
        except (tk.TclError, OSError):
            pass

    def shutdown(self) -> None:
        self._really_quit = True
        self._save_main_geometry()
        try:
            self.disc.save_peer_cache()
        except Exception:
            pass
        if self.tray is not None:
            self.tray.stop()
            self.tray = None
        single_instance.release(self._lock)
        self.disc.stop()
        self.root.destroy()

    def hide_to_tray(self) -> None:
        self._save_main_geometry()
        self._ensure_tray()
        if self.settings.show_taskbar_when_minimized:
            self.root.iconify()
        else:
            self.root.withdraw()
        self._in_tray = True
        if self.tray is not None:
            self.tray.notify("LAN Messenger continua rodando na bandeja.")

    def _ensure_tray(self) -> None:
        """Mantém ícone na área de notificação mesmo com a principal aberta."""
        if self.tray is None and tray_mod is not None and tray_mod.HAVE_TRAY:
            # callbacks do pystray rodam em outra thread: só enfileiram;
            # _pump_tray_cmds executa na thread do Tk.
            self.tray = tray_mod.TrayController(
                on_open=lambda: self._tray_cmds.put("open"),
                on_toggle_status=lambda: self._tray_cmds.put("toggle"),
                on_status=lambda st: self._tray_cmds.put(f"status:{st}"),
                on_quit=lambda: self._tray_cmds.put("quit"),
                icon_path=config.asset_path("app.ico"))
            self.tray.run()

    def _ui_call(self, fn, *args, **kwargs) -> None:
        """Agenda chamada na main thread (after() de worker trava)."""
        try:
            self._ui_queue.put((fn, args, kwargs))
        except Exception:
            pass

    def _pump_ui(self) -> None:
        try:
            while True:
                fn, args, kwargs = self._ui_queue.get_nowait()
                try:
                    fn(*args, **kwargs)
                except (tk.TclError, RuntimeError):
                    pass
                except Exception as e:  # erro de regra não pode parar a fila
                    log_crash(f"ui:{getattr(fn, '__name__', '?')}", e)
        except queue.Empty:
            pass
        if not self._really_quit:
            try:
                self.root.after(100, self._pump_ui)
            except (RuntimeError, tk.TclError):
                pass

    def show_from_tray(self) -> None:
        self._show_from_tray()

    def _pump_tray_cmds(self) -> None:
        try:
            while True:
                cmd = self._tray_cmds.get_nowait()
                try:
                    if cmd == "open":
                        self._show_from_tray()
                    elif cmd == "toggle":
                        self.toggle_status()
                    elif isinstance(cmd, str) and cmd.startswith("status:"):
                        self.set_user_status(cmd.split(":", 1)[1], manual=True)
                    elif cmd == "quit":
                        self.shutdown()
                        return
                except Exception as e:
                    log_crash("tray_cmd", e)
        except queue.Empty:
            pass
        if not self._really_quit:
            self.root.after(250, self._pump_tray_cmds)

    def _show_from_tray(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._in_tray = False
        if self.tray is not None:
            self.tray.set_unread(False)

    def toggle_status(self) -> str:
        new = "away" if self.disc.status == "online" else "online"
        self.set_user_status(new, manual=True)
        return new

    def set_user_status(self, status: str, manual: bool = False,
                        msg: str | None = None) -> None:
        """Altera presença: online/busy/away (botões do rodapé e tray)."""
        if status not in ("online", "busy", "away"):
            return
        self._manual_status = manual and status != "online"
        if msg is None:
            msg = self.disc.status_msg if status == self.disc.status else ""
        self.disc.set_status(status)
        self.disc.update_profile(status_msg=msg)
        if status == "busy":
            self.settings.busy_msg = msg
        elif status == "away":
            self.settings.away_msg = msg
        profile.save(self.profile, self.settings)
        self._last_active = time.time()
        self.refresh()

    def status_button(self, status: str) -> None:
        """Rodapé: Disponível aplica direto; Ocupado/Ausente pede a mensagem."""
        if status == "online":
            self.set_user_status("online", manual=True, msg="")
        else:
            self.status_message_dialog(status)

    def status_message_dialog(self, status: str) -> None:
        """Mensagem por Status com contagem regressiva (estilo clássico)."""
        title = "Ocupado" if status == "busy" else "Ausente"
        default = (self.settings.busy_msg if status == "busy"
                   else self.settings.away_msg)
        win = ctk_dialog(self.root, title, "380x250")
        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(side="bottom", fill="x", padx=10, pady=10)
        remaining = {"n": 10}
        ok_btn = ctk.CTkButton(bot, width=170, text="Definir Status [10]")
        ok_btn.pack(side="left", expand=True)
        ctk.CTkButton(bot, text="Cancelar", width=100,
                      command=win.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkLabel(win, text="Mensagem de status:", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(
                         fill="x", padx=10, pady=(8, 0))
        txt = ctk.CTkTextbox(win, height=80, font=ctk.CTkFont(weight="bold"))
        txt.pack(fill="both", expand=True, padx=10, pady=4)
        txt.insert("1.0", default)
        closed = {"done": False}

        def confirm() -> None:
            if closed["done"]:
                return
            closed["done"] = True
            try:
                win.after_cancel(tick_id["id"])
            except (tk.TclError, KeyError):
                pass
            self.set_user_status(status, manual=True,
                                 msg=txt.get("1.0", "end").strip())
            win.destroy()

        def tick() -> None:
            if closed["done"]:
                return
            try:
                if not win.winfo_exists():
                    return
                ok_btn.configure(text=f"Definir Status [{remaining['n']}]")
                if remaining["n"] <= 0:
                    confirm()
                    return
                remaining["n"] -= 1
                tick_id["id"] = win.after(1000, tick)
            except tk.TclError:
                pass

        tick_id: dict = {}
        ok_btn.configure(command=confirm)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        tick()

    def _update_status_buttons(self) -> None:
        """Botão ativo em negrito; cada um na cor do seu status."""
        for st, b in getattr(self, "_status_buttons", {}).items():
            try:
                active = st == self.disc.status
                b.configure(font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
                            border_width=2 if active else 0)
            except tk.TclError:
                pass

    # -- lista agrupada ------------------------------------------------
    def _auto_refresh(self) -> None:
        self.refresh()
        # sonda periódica: se a VPN derrubou UDP, redescobre sozinho (~12s)
        self._refresh_count += 1
        if self._refresh_count % 4 == 0:
            try:
                self.disc.ping_now()
            except Exception:
                pass
        if self._refresh_count % 20 == 0:
            try:
                self.disc.save_peer_cache()
            except Exception:
                pass
        self.root.after(3000, self._auto_refresh)

    def _recover_peers_async(self) -> None:
        """Volta da queda sem reiniciar: colegas do cache via UDP + TCP."""
        try:
            cache = self.disc.load_peer_cache()
        except Exception:
            cache = {}
        if cache:
            try:
                self.disc.seed_known(cache)
            except Exception:
                pass
            self._roster_sig = ()
            self.refresh()
        try:
            self.disc.ping_now()
        except Exception:
            pass
        ips = [ip for ip in (cache or {})]
        if ips:
            threading.Thread(target=lambda: self._tcp_sweep(ips, per_ip_timeout=2.0),
                             daemon=True, name="tcp-recover").start()

    def _tcp_sweep(self, ips: list[str], per_ip_timeout: float = 2.0) -> bool:
        """Hello TCP em lote (limitado): confirma presença sem UDP."""
        from concurrent.futures import ThreadPoolExecutor
        changed = False

        def one(ip: str) -> bool:
            try:
                reply = chat.fetch_presence(
                    ip, from_name=self.profile.effective_display(),
                    from_user=config.my_user(), key=self.key,
                    timeout=per_ip_timeout)
            except Exception:
                return False
            try:
                return bool(self.disc.note_tcp_beacon(ip, reply))
            except Exception:
                return False

        try:
            with ThreadPoolExecutor(max_workers=8,
                                    thread_name_prefix="tcp-hello") as pool:
                for ok in pool.map(one, list(ips)[:200]):
                    changed = changed or bool(ok)
        except Exception:
            pass
        if changed:
            self._ui_call(self.refresh)
        return changed

    def _tcp_presence_tick(self) -> None:
        """A cada ~10s: hello TCP nos 'sinal fraco' + conhecidos offline."""
        if self._really_quit:
            return
        try:
            targets = self.disc.stale_ips()
            if not targets:
                known = self.disc.snapshot_known()
                targets = [ip for ip, info in known.items()
                           if info.get("status") == "offline"]
            if targets:
                threading.Thread(target=self._tcp_sweep,
                                 args=(targets,), daemon=True,
                                 name="tcp-presence").start()
        except Exception:
            pass
        finally:
            try:
                self.root.after(10000, self._tcp_presence_tick)
            except (RuntimeError, tk.TclError):
                pass

    def _self_ip(self) -> str:
        """Meu IP (conversa própria = anotações, via loopback real)."""
        if getattr(self, "_my_ip", ""):
            return self._my_ip
        ips = [ip for ip in config.my_ips() if not ip.startswith("127.")]
        self._my_ip = ips[0] if ips else "127.0.0.1"
        return self._my_ip

    def _self_info(self) -> dict:
        """Eu como contato (nome, status, IDs e hardware locais)."""
        hw = self.hw_info or {}
        return {"name": config.my_hostname(), "user": config.my_user(),
                "display": self.profile.effective_display(),
                "dept": self.profile.department or "Geral",
                "role": self.profile.role, "status": self.disc.status,
                "anydesk": self.profile.anydesk_id,
                "rustdesk": self.profile.rustdesk_id,
                "cpu": hw.get("cpu", ""), "ram": hw.get("ram", ""),
                "ram_type": hw.get("ram_type", ""), "disk": hw.get("disk", ""),
                "os": hw.get("os", ""), "status_msg": self.disc.status_msg,
                "app_version": config.APP_VERSION,
                "ts": time.time(), "self": True}

    def refresh(self) -> None:
        peers = self.disc.get_roster()
        me = self._self_ip()
        if me not in peers:
            peers[me] = self._self_info()  # eu na lista (anotações)
        groups = roster.group_peers(peers, hide_offline=self.settings.hide_offline,
                                    aliases=self.settings.group_aliases,
                                    hidden=self.settings.hidden_groups,
                                    overrides=self.settings.peer_groups,
                                    custom=self.settings.custom_groups)
        online_now = {ip for ip, p in self.disc.get_peers().items()}
        n_online = len(online_now)
        stale_n = sum(1 for ip in online_now if self.disc.is_stale(ip))
        stale_set = tuple(sorted(ip for ip in online_now if self.disc.is_stale(ip)))
        labels = roster.order_labels(list(groups), self.settings.group_order)
        sig = (tuple(sorted(
            (ip, str(p.get("status", "")), str(p.get("display") or p.get("name", "")),
             str(p.get("dept", ""))) for ip, p in peers.items())),
               tuple(labels), self.settings.hide_offline,
               self._selected_ip, stale_set)
        if sig == self._roster_sig and self.roster_box.winfo_children():
            self.statusbar.configure(
                text=f"Meus Dados: {self.profile.effective_display()} [{status_pt(self.disc.status)}] | "
                     f"{n_online} online"
                     + (f" ({stale_n} sinal fraco)" if stale_n else "")
                     + (" 🔒" if self.key else " (sem cripto)"))
            self._update_status_buttons()
            return
        self._roster_sig = sig
        for w in self.roster_box.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._item_ip.clear()
        self._item_group.clear()
        if self._seen_online is None:
            self._seen_online = online_now  # primeira carga: silenciosa
        else:
            for ip in online_now - self._seen_online:
                sfx.play(self.settings, "user_online")  # "Usuário está online"
            self._seen_online = online_now
        img_group = self._load_icon("usergroup.png", 16)
        img_user = self._load_icon("user.png", 16)
        for dept in labels:
            members = groups[dept]
            open_ = dept not in self._collapsed_groups
            head = ctk.CTkButton(self.roster_box,
                                 text=f"{'▾' if open_ else '▸'} {dept} ({len(members)})",
                                 anchor="w", fg_color="transparent",
                                 text_color=("black", "white"),
                                 font=ctk.CTkFont(weight="bold"),
                                 command=lambda d=dept: self._toggle_group(d))
            if img_group is not None:
                try:
                    head.configure(image=img_group)
                except tk.TclError:
                    pass
            head.pack(fill="x", pady=(4, 0))
            head.bind("<Button-3>", lambda e, d=dept: self._group_popup(e, d), add="+")
            self._item_group[head] = dept
            if not open_:
                continue
            for ip, info in members:
                icon = roster.STATUS_ICON.get(info.get("status", "online"), "?")
                label = roster.label_of(info)
                if info.get("self"):
                    label += " (você)"
                elif info.get("status") == "online" and self.disc.is_stale(ip):
                    label += " (sinal fraco)"
                st_color = ROSTER_STATUS_COLORS.get(info.get("status", "online"),
                                                   ("black", "white"))
                row = ctk.CTkButton(self.roster_box, text=f"{icon} {label}",
                                    anchor="w", fg_color="transparent",
                                    text_color=st_color,
                                    command=lambda i=ip: self._on_user_click(i))
                if img_user is not None:
                    try:
                        row.configure(image=img_user)
                    except tk.TclError:
                        pass
                if ip == self._selected_ip:
                    try:
                        row.configure(fg_color=("gray75", "gray30"))
                    except tk.TclError:
                        pass
                row.pack(fill="x", padx=(16, 0))
                row.bind("<Double-Button-1>", lambda e, i=ip: self.open_chat(i), add="+")
                row.bind("<Button-3>", lambda e, i=ip: self._user_popup(e, i), add="+")
                self._item_ip[row] = ip
        self.statusbar.configure(
            text=f"Meus Dados: {self.profile.effective_display()} [{status_pt(self.disc.status)}] | "
                 f"{n_online} online"
                 + (f" ({stale_n} sinal fraco)" if stale_n else "")
                 + (" 🔒" if self.key else " (sem cripto)"))
        self._update_status_buttons()

    def _on_user_click(self, ip: str) -> None:
        """Um clique seleciona; duplo abre a conversa (abre direto, simples)."""
        self._selected_ip = ip
        self._selected_group = ""
        self.open_chat(ip)

    def _user_popup(self, event, ip: str) -> str:
        self._selected_ip = ip
        self._selected_group = ""
        self._user_menu(ip).tk_popup(event.x_root, event.y_root)
        return "break"  # não propaga p/ o menu do fundo

    def _group_popup(self, event, dept: str) -> str:
        self._selected_group = dept
        self._group_menu(dept).tk_popup(event.x_root, event.y_root)
        return "break"  # não propaga p/ o menu do fundo

    def _bg_popup(self, event) -> str:
        self._bg_menu().tk_popup(event.x_root, event.y_root)
        return "break"

    def selected_ip(self, silent: bool = False) -> str:
        if self._selected_ip and self._selected_ip in self.disc.get_roster():
            return self._selected_ip
        # cai para o primeiro online (compat com testes antigos)
        for ip in self.disc.get_roster():
            return ip
        if not silent:
            messagebox.showinfo("Usuários", "Selecione um usuário na lista.")
        return ""

    def selected_info(self, ip: str) -> dict:
        if ip == self._self_ip():
            return self._self_info()
        return self.disc.get_roster().get(ip, {"display": ip, "dept": "Geral"})

    def peer_label(self, ip: str) -> str:
        return roster.label_of(self.selected_info(ip))

    def seen_age_str(self, ip: str) -> str:
        """'há 12s' desde o último beacon (fidelidade: sabe se está fresco)."""
        if ip == self._self_ip():
            return "agora"
        age = self.disc.peer_age(ip)
        if age == float("inf"):
            return "nunca visto"
        return f"há {max(0, int(age))}s"  # relógio do colega adiantado: nunca negativo

    # -- cliques e menus de contexto (estilo clássico) ---------------------
    def _on_left_click(self, event) -> None:
        """Compat: um clique no usuário abre a conversa."""

    def _on_right_click(self, event) -> None:
        """Compat: menu de contexto (lógica vive nos popups das linhas)."""

    def _row_at(self, x: int, y: int) -> str:
        return ""

    def _selected_group(self, silent: bool = True) -> str:
        return self._selected_group

    def _on_tree_key(self, event) -> None:
        """Enter/F2/Del/Ctrl+Up/Ctrl+Down (atalhos clássicos na lista)."""
        key = getattr(event, "keysym", "")
        if key == "Return" and self._selected_ip:
            self.open_chat(self._selected_ip)
        elif key == "F2" and self._selected_group:
            self.rename_group(self._selected_group)
        elif key in ("Delete", "BackSpace") and self._selected_group:
            self.delete_group(self._selected_group)
        elif key in ("Up", "Down") and (getattr(event, "state", 0) & 0x4):
            if self._selected_group:
                self.move_group(self._selected_group, -1 if key == "Up" else 1)

    def _group_menu(self, dept: str) -> tk.Menu:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Enviar Mensagem para o Grupo",
                      command=lambda: self.send_to_group_dialog(dept))
        m.add_command(label="Start Group Conversation",
                      command=lambda: self.open_group_chat(dept))
        m.add_command(label="Renomear Grupo...", command=lambda: self.rename_group(dept))
        m.add_command(label="Adicionar Novo Grupo...", command=self.add_group_dialog)
        m.add_command(label="Apagar Grupo", command=lambda: self.delete_group(dept))
        m.add_command(label="Mover Grupo para Cima",
                      command=lambda: self.move_group(dept, -1))
        m.add_command(label="Mover Grupo para Baixo",
                      command=lambda: self.move_group(dept, 1))
        return m

    def _original_of(self, label: str) -> str:
        """Nome original do grupo (antes do apelido)."""
        for orig, alias in self.settings.group_aliases.items():
            if alias == label:
                return orig
        return label

    def send_to_group_dialog(self, dept: str) -> None:
        """Enviar Mensagem para o Grupo: massa com o grupo pré-marcado."""
        groups = roster.group_peers(self.disc.get_roster(), hide_offline=True,
                                    aliases=self.settings.group_aliases,
                                    hidden=self.settings.hidden_groups,
                                    overrides=self.settings.peer_groups,
                                    custom=self.settings.custom_groups)
        if dept not in groups:
            messagebox.showinfo("Grupo", f"Grupo '{dept}' sem membros online.")
            return

        def send(ips: list[str], text: str) -> dict[str, str]:
            return chat.send_broadcast(
                ips, text, from_name=self.profile.effective_display(),
                from_user=config.my_user(), key=self.key)
        mass.open_mass_dialog(self.root, groups, send, preselect=[dept])

    def open_group_chat(self, dept: str) -> None:
        """Start Group Conversation: janela persistente com fan-out."""
        w = self.group_windows.get(dept)
        if w and w.win.winfo_exists():
            w.win.lift()
            return
        self.group_windows[dept] = GroupChatWindow(self, dept)

    def rename_group(self, dept: str) -> None:
        """Renomear Grupo... (F2): grava apelido."""
        from tkinter import simpledialog
        orig = self._original_of(dept)
        new = simpledialog.askstring("Renomear Grupo", f"Novo nome para '{dept}':",
                                     initialvalue=dept, parent=self.root)
        if not new or not new.strip() or new.strip() == dept:
            return
        new = new.strip()
        if orig == dept and dept in self.settings.custom_groups:
            self.settings.custom_groups = [new if g == dept else g
                                           for g in self.settings.custom_groups]
            self.settings.peer_groups = {k: (new if v == dept else v)
                                         for k, v in self.settings.peer_groups.items()}
        else:
            self.settings.group_aliases[orig] = new
        profile.save(self.profile, self.settings)
        if dept in self.group_windows:
            self.group_windows.pop(dept).win.destroy()
        self.refresh()

    def delete_group(self, dept: str) -> None:
        """Apagar Grupo (Del): custom apaga; automático oculta."""
        orig = self._original_of(dept)
        if orig in self.settings.custom_groups or dept in self.settings.custom_groups:
            target = orig if orig in self.settings.custom_groups else dept
            if not messagebox.askyesno("Apagar Grupo",
                                       f"Apagar o grupo '{dept}'?", parent=self.root):
                return
            self.settings.custom_groups = [g for g in self.settings.custom_groups if g != target]
            self.settings.peer_groups = {k: v for k, v in self.settings.peer_groups.items()
                                         if v != target}
            self.settings.group_aliases.pop(target, None)
            self.settings.group_order = [g for g in self.settings.group_order if g != dept]
            if dept in self.group_windows:
                self.group_windows.pop(dept).win.destroy()
        else:
            if not messagebox.askyesno("Apagar Grupo",
                                       f"'{dept}' é automático (volta sozinho).\n"
                                       f"Ocultar em vez de apagar?", parent=self.root):
                return
            if orig not in self.settings.hidden_groups:
                self.settings.hidden_groups.append(orig)
        profile.save(self.profile, self.settings)
        self.refresh()

    def move_group(self, dept: str, delta: int) -> None:
        """Mover Grupo para Cima/Baixo (Ctrl+Up/Down)."""
        labels = roster.order_labels(
            list(roster.group_peers(self.disc.get_roster(),
                                    aliases=self.settings.group_aliases,
                                    hidden=self.settings.hidden_groups,
                                    overrides=self.settings.peer_groups,
                                    custom=self.settings.custom_groups)),
            self.settings.group_order)
        if dept not in labels:
            labels.append(dept)
        i = labels.index(dept)
        j = max(0, min(len(labels) - 1, i + delta))
        if i != j:
            labels[i], labels[j] = labels[j], labels[i]
            self.settings.group_order = labels
            profile.save(self.profile, self.settings)
            self.refresh()

    def _user_menu(self, ip: str) -> tk.Menu:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Iniciar Conversa", command=lambda: self.open_chat(ip))
        m.add_command(label="Enviar Mensagem em Massa", command=self.mass_dialog)
        m.add_command(label="Enviar Arquivo(s)...",
                      command=lambda: (self.open_chat(ip),
                                       self.chat_windows[ip].send_file()))
        m.add_command(label="Ping (CMD: 5 disparos)",
                      command=lambda: self._cmd_ping(ip))
        m.add_command(label="Conectar via AnyDesk",
                      command=lambda: self._remote_connect(ip, "anydesk"))
        m.add_command(label="Conectar via RustDesk",
                      command=lambda: self._remote_connect(ip, "rustdesk"))
        m.add_command(label="Ver Informações",
                      command=lambda: self.peer_info_dialog(ip))
        move = tk.Menu(m, tearoff=0)
        move.add_command(label="(Automático: departamento de origem)",
                         command=lambda: self._move_peer(ip, None))
        for dept in self._known_depts():
            move.add_command(label=dept, command=lambda d=dept: self._move_peer(ip, d))
        m.add_cascade(label="Mover Usuário para ...", menu=move)
        return m

    def _bg_menu(self) -> tk.Menu:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Atualizar Lista de Usuários", command=self.refresh_now)
        m.add_command(label="Adicionar Novo Grupo...", command=self.add_group_dialog)
        m.add_command(label="Enviar Mensagem em Massa", command=self.mass_dialog)
        hide = tk.BooleanVar(value=self.settings.hide_offline)

        def toggle() -> None:
            self.settings.hide_offline = hide.get()
            profile.save(self.profile, self.settings)
            self.refresh()
        m.add_checkbutton(label="Ocultar Usuários Offline", variable=hide, command=toggle)
        return m

    def refresh_now(self) -> None:
        """Atualizar agora: sonda UDP + redesenha (botão direito no vazio)."""
        try:
            self.disc.ping_now()
        except Exception:
            pass
        self._roster_sig = ()
        self.refresh()

    def _known_depts(self) -> list[str]:
        depts = {("Geral" if str(i.get("dept") or "Geral") == "General"
                  else str(i.get("dept") or "Geral"))
                 for i in self.disc.get_roster().values()}
        depts.update(self.settings.custom_groups)
        return sorted(depts, key=str.lower)

    def _move_peer(self, ip: str, dept: str | None) -> None:
        key = roster.peer_key(self.selected_info(ip))
        if dept is None:
            self.settings.peer_groups.pop(key, None)
        else:
            self.settings.peer_groups[key] = dept
        profile.save(self.profile, self.settings)
        self.refresh()

    def _cmd_ping(self, ip: str) -> None:
        """Ping: abre o CMD com 5 disparos para o IP do contato."""
        try:
            remote.open_cmd_ping(ip)
        except (ValueError, OSError) as e:
            messagebox.showerror("Ping", str(e), parent=self.root)

    def _remote_connect(self, ip: str, kind: str) -> None:
        """Conectar via AnyDesk/RustDesk usando o ID anunciado do contato."""
        info = self.selected_info(ip)
        id_ = (info.get("anydesk") if kind == "anydesk" else info.get("rustdesk")) or ""
        id_ = remote.clean_id(str(id_))
        if not id_:
            messagebox.showinfo(
                "Acesso remoto",
                f"{self.peer_label(ip)} não cadastrou ID de "
                f"{'AnyDesk' if kind == 'anydesk' else 'RustDesk'}.\n"
                f"Peça p/ preencher em Meus Dados.", parent=self.root)
            return
        try:
            if kind == "anydesk":
                remote.connect_anydesk(id_)
            else:
                remote.connect_rustdesk(id_)
        except (ValueError, OSError) as e:
            messagebox.showerror("Acesso remoto", str(e), parent=self.root)

    def peer_info_dialog(self, ip: str) -> None:
        """Ver Informações do usuário."""
        info = self.selected_info(ip)
        win = ctk_dialog(self.root, f"{roster.label_of(info)} - Informações",
                         "540x520")
        rows = [("Nome:", roster.label_of(info)),
                ("Usuário:", str(info.get("user", "?"))),
                ("Departamento:", str(info.get("dept", "Geral"))),
                ("Cargo:", str(info.get("role", "") or "-")),
                ("IP:", ip),
                ("Status:", status_pt(str(info.get("status", "online")))),
                ("Versão LAN Messenger:", str(info.get("app_version", "") or "-")),
                ("Visto há:", self.seen_age_str(ip)),
                ("Mensagem:", str(info.get("status_msg", "") or "-")),
                ("AnyDesk ID:", str(info.get("anydesk", "") or "-")),
                ("RustDesk ID:", str(info.get("rustdesk", "") or "-")),
                ("Sistema:", str(info.get("os", "") or "-")),
                ("Processador:", str(info.get("cpu", "") or "-")),
                ("Memória RAM:", (str(info.get("ram", "") or "-") +
                                  (f" ({info.get('ram_type')})" if info.get("ram_type") else ""))),
                ("Disco:", str(info.get("disk", "") or "-"))]
        for label, value in rows:
            f = ctk.CTkFrame(win, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(f, text=label, width=130, anchor="w",
                         text_color="gray").pack(side="left")
            ctk.CTkLabel(f, text=value, anchor="w",
                         wraplength=360, justify="left").pack(
                             side="left", fill="x", expand=True)
        ctk.CTkButton(win, text="Fechar", width=100,
                      command=win.destroy).pack(pady=8)

    def add_group_dialog(self) -> None:
        """Adicionar Novo Grupo... (menu do vazio)."""
        from tkinter import simpledialog
        name = simpledialog.askstring("Novo Grupo", "Nome do grupo:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        if name not in self.settings.custom_groups:
            self.settings.custom_groups.append(name)
            profile.save(self.profile, self.settings)
            self.refresh()

    # -- conversa -------------------------------------------------------
    def open_selected(self) -> None:
        ip = self.selected_ip()
        if ip:
            self.open_chat(ip)

    def open_chat(self, ip: str) -> None:
        w = self.chat_windows.get(ip)
        if w and w.win.winfo_exists():
            self._activate_chat_window(w)
            return
        self.chat_windows[ip] = ChatWindow(self, ip, self.selected_info(ip))
        self._activate_chat_window(self.chat_windows[ip])

    def _activate_chat_window(self, w) -> None:
        """Traz a conversa para frente e foca o campo de digitação."""
        for delay in (0, 60, 180):
            try:
                w.win.after(delay, self._lift_chat_window, w)
            except tk.TclError:
                break

    def _lift_chat_window(self, w) -> None:
        try:
            w.win.deiconify()
        except tk.TclError:
            pass
        try:
            w.win.lift()
        except tk.TclError:
            pass
        try:
            w.win.focus_force()
        except tk.TclError:
            pass
        try:
            w._focus_entry()
        except tk.TclError:
            pass

    def on_msg_threadsafe(self, msg: dict, ip: str) -> None:
        self._ui_call(self._on_msg, msg, ip)

    def _bring_to_front(self) -> None:
        """Traz a principal para frente (clique na notificação/toast)."""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass
        except Exception as e:
            log_crash("bring_to_front", e)

    def _notify(self, title: str, text: str, on_click=None) -> None:
        """Notificação: toast do sistema (Win10/11); senão balão da bandeja.

        on_click só vale para o toast (clique); é despachado pela fila da
        UI, pois o WinRT chama o callback em outra thread.
        """
        cb = (lambda: self._ui_call(on_click)) if on_click is not None else None
        if self.settings.toast_enabled and toaster.notify(title, text, cb):
            return
        if self._in_tray and self.tray is not None:
            self.tray.notify(text, title)

    def _mentioned(self, text: str) -> bool:
        return mentioned_me(text, self.profile.effective_display(),
                            config.my_user())

    def _autodetect_ids(self) -> None:
        """Preenche IDs vazios lendo o AnyDesk/RustDesk locais (ao iniciar)."""
        p = self.profile
        ad = p.anydesk_id or remote.get_anydesk_id()
        rd = p.rustdesk_id or remote.get_rustdesk_id()
        if (ad, rd) == (p.anydesk_id, p.rustdesk_id):
            return
        p.anydesk_id, p.rustdesk_id = ad, rd
        profile.save(p, self.settings)
        self._ui_call(self.disc.update_profile,
                      display=p.effective_display(), dept=p.department, role=p.role,
                      anydesk=ad, rustdesk=rd, hw=self.hw_info)

    def _on_msg(self, msg: dict, ip: str) -> None:
        text = str(msg.get("text", ""))
        mid = str(msg.get("id", ""))
        raw = msg.get("reply")
        reply = raw if isinstance(raw, dict) and raw.get("id") else None
        self.store.add_message(mid, ip, "in", text)
        if reply:  # v1.30: guarda a citação p/ reabrir a conversa
            self.store.set_reply(mid, str(reply.get("id", "")),
                                 str(reply.get("name", ""))[:80],
                                 str(reply.get("text", ""))[:300])
        logger.log_message(self.settings, self.peer_label(ip), "in", text)
        # conversa em grupo aberta com este remetente? vai p/ lá (sem 1-1)
        gw = self._group_window_for(ip)
        if msg.get("bcast") and gw is not None:
            mentioned = self._mentioned(text)
            gw.incoming(ip, self.selected_info(ip), text, mention=mentioned)
            self.touch()
            gw_focused = False
            try:
                gw_focused = bool(gw.win.focused)
            except tk.TclError:
                pass
            if mentioned and not gw_focused:
                if self._in_tray and self.tray is not None:
                    self.tray.set_unread(True)
                self._notify("Você foi mencionado",
                             f"{self.peer_label(ip)} no grupo {gw.dept}: "
                             f"{text[:110]}", on_click=self._bring_to_front)
            elif self._in_tray and self.tray is not None:
                self.tray.set_unread(True)
                self._notify("Mensagem em grupo",
                             f"[{gw.dept}] {self.peer_label(ip)}: {text[:120]}")
            # som de broadcast (sem repetição; repetição é só p/ 1-1)
            if not (self.settings.snd_msg_mode == "background" and gw.win.focused):
                sfx.play(self.settings, "broadcast")
            return
        w = self.chat_windows.get(ip)
        if self.settings.incoming_behavior == "minimize":
            # minimiza na barra: sem popup; avisa na statusbar + som
            self.statusbar.configure(text=f"Nova mensagem de {self.peer_label(ip)}")
            if w and w.win.winfo_exists():
                w.incoming(text, self.selected_info(ip), mid=mid, reply=reply)
        elif w and w.win.winfo_exists():
            w.incoming(text, self.selected_info(ip), mid=mid, reply=reply)
        else:
            self.open_chat(ip)
            self.chat_windows[ip].incoming(text, self.selected_info(ip),
                                           mid=mid, reply=reply)
        self.touch()
        if self._in_tray and self.tray is not None:
            self.tray.set_unread(True)
            # broadcast com @meu-nome (janela de grupo fechada): avisa menção
            if msg.get("bcast") and self._mentioned(text):
                self._notify("Você foi mencionado",
                             f"{self.peer_label(ip)}: {text[:110]}",
                             on_click=self._bring_to_front)
            else:
                self._notify(f"{self.peer_label(ip)}: {text[:120]}",
                             "Mensagem recebida")
        # -- sons (tela Eventos de Som) --
        event = "broadcast" if msg.get("bcast") else "message"
        w2 = self.chat_windows.get(ip)
        window_active = False
        try:
            window_active = bool(w2 and w2.win.winfo_exists() and w2.focused)
        except tk.TclError:
            pass
        if self.settings.snd_msg_mode == "background" and window_active:
            pass  # conversa em primeiro plano: sem som
        elif sfx.play(self.settings, event):
            if self.settings.snd_repeat:
                self._repeat_tick(ip, event, 0)

    def _group_window_for(self, ip: str):
        """Janela de grupo aberta que contém o remetente (ou None)."""
        for dept, w in list(self.group_windows.items()):
            if not w.win.winfo_exists():
                self.group_windows.pop(dept, None)
                continue
            try:
                if ip in w.members():
                    return w
            except tk.TclError:
                continue
        return None

    def _repeat_tick(self, ip: str, event: str, count: int) -> None:
        """Repete o som até a conversa ficar ativa (ou 12x)."""
        if count >= 12:
            return
        w = self.chat_windows.get(ip)
        if w is None or not w.win.winfo_exists() or w.focused:
            return
        sfx.play(self.settings, event)
        self.root.after(self.settings.snd_repeat_sec * 1000,
                        lambda: self._repeat_tick(ip, event, count + 1))

    def on_file_threadsafe(self, header: dict, path: Path, ip: str = "") -> None:
        logger.log_file_event(self.settings, str(header.get("from_name", "?")),
                              "in", str(header.get("filename", "")))
        self._ui_call(self._on_file_ui, header, str(path), ip)

    def _on_file_ui(self, header: dict, path: str, ip: str) -> None:
        sfx.play(self.settings, "file")  # "Arquivo recebido"
        try:
            size_bytes = Path(path).stat().st_size
        except OSError:
            size_bytes = 0
        size_kb = size_bytes / 1024
        text = (f"1 arquivo(s) ({size_kb:,.0f} KB) recebido(s)".replace(",", "."))
        fname = str(header.get("filename", ""))
        self.store.add_message(f"file-in-{time.time_ns()}-{ip}", ip, "in",
                               file_history_text("recebido", fname, size_bytes))
        w = self.chat_windows.get(ip) if ip else None
        if w is not None and w.win.winfo_exists():
            w._xfer_show("recv")
            w._xfer_done(text, path)
            w._append_file_line(fname, size_kb, path)
        else:
            if ip:
                self.open_chat(ip)
                w2 = self.chat_windows.get(ip)
                if w2 is not None and w2.win.winfo_exists():
                    w2._xfer_show("recv")
                    w2._xfer_done(text, path)
                    w2._append_file_line(fname, size_kb, path)
                    return
            messagebox.showinfo("Arquivo recebido", f"{header.get('filename')} salvo.")

    # -- aceite de arquivos (tela Transferência: "Pergunte...") ----------
    def _file_request(self, header: dict) -> bool:
        """Roda na thread do FileServer. Bloqueia o ACK até o usuário decidir."""
        sender = str(header.get("from_name", "?"))
        if self.settings.file_accept == "auto" or sender in self.settings.approved_senders:
            return True
        box: dict = {}
        done = threading.Event()
        self._file_asks.put((header, sender, box, done))
        finished = done.wait(timeout=180)
        return finished and box.get("accept", False)

    def _pump_file_asks(self) -> None:
        try:
            while True:
                header, sender, box, done = self._file_asks.get_nowait()
                try:
                    self._ask_file_dialog(header, sender, box, done)
                except Exception as e:  # diálogo falhou: libera o worker
                    done.set()
                    log_crash("file_ask", e)
        except queue.Empty:
            pass
        self.root.after(250, self._pump_file_asks)

    def _ask_file_dialog(self, header: dict, sender: str,
                         box: dict, done: threading.Event) -> None:
        fname = str(header.get("filename", "?"))
        try:
            size = int(header.get("size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        win = ctk_dialog(self.root, "Arquivo recebido", "440x180")
        ctk.CTkLabel(win, text=f"{sender} quer enviar:", anchor="w").pack(
            fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(win, text=f"{fname} ({size // 1024} KB)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(padx=10, pady=4)

        def decide(accept: bool, always: bool = False) -> None:
            if always and accept and sender not in self.settings.approved_senders:
                self.settings.approved_senders.append(sender)
                profile.save(self.profile, self.settings)
            box["accept"] = accept
            done.set()
            win.destroy()
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="Aceitar", width=90,
                      command=lambda: decide(True)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Sempre aceitar", width=130,
                      command=lambda: decide(True, always=True)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Recusar", width=90,
                      command=lambda: decide(False)).pack(side="left", padx=4)
        win.protocol("WM_DELETE_WINDOW", lambda: decide(False))
        win.bind("<Escape>", lambda _e: decide(False), add="+")

    # -- diálogos --------------------------------------------------------
    def add_manual(self) -> None:
        from tkinter import simpledialog
        ip = simpledialog.askstring("IP manual", "IP do colega (ex 192.168.1.20):",
                                    parent=self.root)
        if ip:
            self.disc.add_peer_manual(ip.strip())
            self.refresh()

    def edit_ranges(self) -> None:
        """Equivalente à tela Rede (Transmissão/Broadcasts)."""
        from tkinter import simpledialog
        win = ctk_dialog(self.root, "Rede - Faixas de transmissão (VPN)",
                         "480x660", resizable=(True, True))
        ctk.CTkLabel(win, text="Faixas ex 10.0.0.1-10.0.0.254 (atravessam VPN):").pack(
            anchor="w", padx=6, pady=4)
        lst = tk.Listbox(win)
        lst.pack(fill="both", expand=True, padx=6)
        for r in self.disc.get_ranges():
            lst.insert("end", r)

        def refresh_lst() -> None:
            lst.delete(0, "end")
            for r in self.disc.get_ranges():
                lst.insert("end", r)

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=4)

        def on_add() -> None:
            spec = simpledialog.askstring("Adicionar faixa",
                                          "Faixa (ex 192.168.30.1-192.168.30.254):",
                                          parent=win)
            if not spec:
                return
            try:
                self.disc.add_range(spec.strip())
                refresh_lst()
            except ValueError as e:
                messagebox.showerror("Faixa inválida", str(e), parent=win)

        def on_del() -> None:
            sel = lst.curselection()
            if sel:
                self.disc.del_range(lst.get(sel[0]))
                refresh_lst()
        ctk.CTkButton(btns, text="Adicionar...", width=100,
                      command=on_add).pack(side="left")
        ctk.CTkButton(btns, text="Apagar", width=90,
                      command=on_del).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="+ IP manual", width=100,
                      command=self.add_manual).pack(side="left", padx=4)

        # -- criptografia PSK (mesma chave em todos os PCs) --
        ctk.CTkLabel(win, text="Chave de criptografia (PSK) — igual em todos os PCs:",
                     anchor="w").pack(fill="x", padx=6, pady=(6, 0))
        kf = ctk.CTkFrame(win, fg_color="transparent")
        kf.pack(fill="x", padx=6, pady=2)
        key_var = tk.StringVar(value=self.settings.crypto_key)
        ctk.CTkEntry(kf, textvariable=key_var, show="*", width=260).pack(
            side="left", fill="x", expand=True)

        def on_gen() -> None:
            key_var.set(crypto.generate_key())

        def on_export() -> None:
            val = key_var.get().strip() or self.settings.crypto_key.strip()
            if not val or crypto.parse_key(val) is None:
                messagebox.showinfo("Exportar chave", "Gere ou informe uma chave válida primeiro.",
                                    parent=win)
                return
            dest = filedialog.asksaveasfilename(
                parent=win, defaultextension=".key", initialfile="lan-chave.key",
                filetypes=[("Chave LAN", "*.key")])
            if not dest:
                return
            try:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(val.strip() + "\n")
                messagebox.showinfo("Exportar chave",
                                    f"Salva em {dest}\nLeve ao outro PC e use Importar.",
                                    parent=win)
            except OSError as e:
                messagebox.showerror("Exportar chave", str(e), parent=win)

        def on_import() -> None:
            src = filedialog.askopenfilename(
                parent=win, filetypes=[("Chave LAN", "*.key"), ("Todos", "*.*")])
            if not src:
                return
            try:
                with open(src, encoding="utf-8") as f:
                    val = f.read().strip().split()[0]
            except (OSError, IndexError) as e:
                messagebox.showerror("Importar chave", f"Arquivo inválido: {e}", parent=win)
                return
            if crypto.parse_key(val) is None:
                messagebox.showerror("Importar chave", "Chave inválida no arquivo.", parent=win)
                return
            key_var.set(val)

        def on_save_key() -> None:
            val = key_var.get().strip()
            if val and crypto.parse_key(val) is None:
                messagebox.showerror("Chave inválida",
                                     "Use Gerar ou cole uma chave válida (32 bytes base64).",
                                     parent=win)
                return
            self.settings.crypto_key = val
            profile.save(self.profile, self.settings)
            self._apply_key()
            messagebox.showinfo("Rede", "Chave salva. Distribua o mesmo valor aos demais PCs.",
                                parent=win)
        ctk.CTkButton(kf, text="Gerar", width=70, command=on_gen).pack(side="left", padx=2)
        ctk.CTkButton(kf, text="Exportar", width=80, command=on_export).pack(side="left")
        ctk.CTkButton(kf, text="Importar", width=80, command=on_import).pack(side="left", padx=2)
        ctk.CTkButton(kf, text="Salvar", width=70, command=on_save_key).pack(side="left")
        ctk.CTkLabel(win, text="Sem chave = tráfego em claro. Beacons e nomes de arquivo seguem visíveis.",
                     text_color="gray").pack(padx=6, pady=2)

        # -- diagnóstico de descoberta (lista vazia? comece aqui) --
        ctk.CTkLabel(win, text="Diagnóstico:", font=ctk.CTkFont(weight="bold"),
                     anchor="w").pack(fill="x", padx=6, pady=(6, 0))
        diag_txt = ctk.CTkLabel(win, text="", anchor="w", justify="left",
                                text_color="gray")
        diag_txt.pack(fill="x", padx=6)

        def fmt_age(ts: float) -> str:
            if not ts:
                return "nunca"
            return f"há {int(time.time() - ts)}s"

        def refresh_diag() -> None:
            d = self.disc.diag()
            bind = ("OK" if d["bind_ok"] else
                    ("?" if d["bind_ok"] is None else f"ERRO: {d['bind_error']}"))
            diag_txt.configure(
                text=f"Escuta UDP {d['udp_port']}: {bind} | destinos: {d['targets']}\n"
                     f"Último envio: {fmt_age(d['last_tx'])} ({d['tx_count']} ok, "
                     f"{d['tx_errors']} falhas) | "
                     f"Último recebido: {fmt_age(d['last_rx'])}"
                     + (f" de {d['last_rx_from']}" if d["last_rx"] else "") +
                     f"\nOnline agora: {d['online']} | já vistos: {d['known']}")
        refresh_diag()
        tf = ctk.CTkFrame(win, fg_color="transparent")
        tf.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(tf, text="Testar IP:").pack(side="left")
        tip_var = tk.StringVar()
        ctk.CTkEntry(tf, textvariable=tip_var, width=140).pack(side="left", padx=4)
        res = ctk.CTkLabel(tf, text="", text_color="gray")
        res.pack(side="left")

        def on_test() -> None:
            ip = tip_var.get().strip()
            if not ip:
                return
            res.configure(text="testando...")
            ok, msg = networks.tcp_ping(ip, config.TCP_CHAT_PORT)
            res.configure(text=f"TCP 50001: {msg}",
                          text_color="green" if ok else "red")
            if ok:
                self.disc.add_peer_manual(ip, name=f"{ip} (testado)")
                refresh_diag()
        ctk.CTkButton(tf, text="Testar", width=80, command=on_test).pack(side="left", padx=2)
        ctk.CTkButton(tf, text="Atualizar", width=90, command=refresh_diag).pack(side="left")
        ctk.CTkLabel(win, text="Testar OK + lista vazia = UDP bloqueado (firewall/VPN).",
                     text_color="gray").pack(padx=6, pady=2)

    def _field(self, parent, label: str, value: str):
        ctk.CTkLabel(parent, text=label, anchor="w").pack(fill="x", padx=8)
        e = ctk.CTkEntry(parent)
        e.pack(fill="x", padx=8, pady=(0, 6))
        e.insert(0, value)
        return e

    def my_data_dialog(self) -> None:
        """Tela Informações do Usuário (OK sempre visível)."""
        win = ctk_dialog(self.root, "Minhas Informações Pessoais",
                         "440x640", resizable=(True, True))
        p = self.profile
        form = ctk.CTkScrollableFrame(win)
        form.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        fields: dict[str, ctk.CTkEntry] = {}
        fields["Nome do usuário (a ser exibido na lista):"] = self._field(
            form, "Nome do usuário (a ser exibido na lista):", p.display_name)
        fields["Primeiro nome:"] = self._field(form, "Primeiro nome:", p.first_name)
        fields["Último nome:"] = self._field(form, "Último nome:", p.last_name)
        fields["Departamento:"] = self._field(form, "Departamento:", p.department)
        fields["Cargo:"] = self._field(form, "Cargo:", p.role)
        fields["AnyDesk ID:"] = self._field(form, "AnyDesk ID:", p.anydesk_id)
        fields["RustDesk ID:"] = self._field(form, "RustDesk ID:", p.rustdesk_id)

        def detect() -> None:
            """Preenche os IDs lendo o AnyDesk/RustDesk desta máquina."""
            btn.configure(state="disabled", text="Detectando...")

            def run() -> None:
                ad = remote.get_anydesk_id()
                rd = remote.get_rustdesk_id()

                def apply() -> None:
                    try:
                        btn.configure(state="normal", text="Detectar IDs")
                    except tk.TclError:
                        return
                    if ad:
                        fields["AnyDesk ID:"].delete(0, "end")
                        fields["AnyDesk ID:"].insert(0, ad)
                    if rd:
                        fields["RustDesk ID:"].delete(0, "end")
                        fields["RustDesk ID:"].insert(0, rd)
                    if not ad and not rd:
                        messagebox.showinfo(
                            "Detectar IDs",
                            "AnyDesk/RustDesk não encontrados nesta máquina.",
                            parent=win)
                win.after(0, apply)
            threading.Thread(target=run, daemon=True).start()

        btn = ctk.CTkButton(win, text="Detectar IDs", command=detect)
        btn.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(win, text="Detecta os IDs locais do AnyDesk/RustDesk (sem digitar).",
                     text_color="gray", anchor="w").pack(fill="x", padx=8)
        ctk.CTkLabel(win, text="Informações adicionais:", anchor="w").pack(fill="x", padx=8)
        info = ctk.CTkTextbox(win, height=80)
        info.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        info.insert("1.0", p.info)

        def ok() -> None:
            p.display_name = fields["Nome do usuário (a ser exibido na lista):"].get()
            p.first_name = fields["Primeiro nome:"].get()
            p.last_name = fields["Último nome:"].get()
            p.department = fields["Departamento:"].get() or "Geral"
            p.role = fields["Cargo:"].get()
            p.anydesk_id = remote.clean_id(fields["AnyDesk ID:"].get())
            p.rustdesk_id = remote.clean_id(fields["RustDesk ID:"].get())
            p.info = info.get("1.0", "end").strip()
            profile.save(p, self.settings)
            self.disc.update_profile(display=p.effective_display(),
                                     dept=p.department, role=p.role,
                                     anydesk=p.anydesk_id, rustdesk=p.rustdesk_id,
                                     hw=self.hw_info)
            self.refresh()
            win.destroy()

        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(bot, text="OK", width=100, command=ok).pack(side="right")
        ctk.CTkButton(bot, text="Cancelar", width=100,
                      command=win.destroy).pack(side="right", padx=6)

    def general_dialog(self) -> None:
        self.settings_dialog()

    def settings_dialog(self) -> None:
        """Configurações (Geral + Transferência de Arquivo + Log), estilo clássico."""
        win = ctk_dialog(self.root, "Configurações", "520x560",
                         resizable=(True, True))
        nb = ctk.CTkTabview(win)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        s = self.settings

        # -- aba Geral --
        nb.add("Geral")
        g = nb.tab("Geral")
        ctk.CTkLabel(g, text="Lista do Usuário",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=4)
        f = ctk.CTkFrame(g, fg_color="transparent")
        f.pack(fill="x", padx=8)
        ctk.CTkLabel(f, text="Ausente após inatividade por").pack(side="left")
        away = tk.StringVar(value=str(s.away_after_min))
        ctk.CTkEntry(f, textvariable=away, width=50).pack(side="left", padx=4)
        ctk.CTkLabel(f, text="minuto(s)").pack(side="left")
        hide = tk.BooleanVar(value=s.hide_offline)
        ctk.CTkCheckBox(g, text="Ocultar usuários offline", variable=hide).pack(
            anchor="w", padx=8)
        auto = tk.BooleanVar(value=s.autostart)
        ctk.CTkCheckBox(g, text="Iniciar com o Windows", variable=auto).pack(
            anchor="w", padx=8)
        tf = ctk.CTkFrame(g, fg_color="transparent")
        tf.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(tf, text="Tema:").pack(side="left")
        v_theme = tk.StringVar(value=s.theme if s.theme in ("Light", "Dark", "System") else "Light")

        def _apply_theme_live(choice: str) -> None:
            if choice in ("Light", "Dark", "System"):
                try:
                    ctk.set_appearance_mode(choice)
                except (tk.TclError, ValueError):
                    pass

        ctk.CTkOptionMenu(tf, variable=v_theme,
                          values=["Light", "Dark", "System"],
                          command=_apply_theme_live,
                          width=130).pack(side="left", padx=8)
        ctk.CTkButton(g, text="Configurações dos Grupos...", width=220,
                      command=lambda: self.groups_dialog(win)).pack(
                          anchor="w", padx=8, pady=4)

        # -- aba Mensagens (Janela de Mensagem + Fonte) --
        nb.add("Mensagens")
        m = nb.tab("Mensagens")
        ctk.CTkLabel(m, text="Janela de Mensagem",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=4)
        v_recent = tk.BooleanVar(value=s.show_recent)
        ctk.CTkCheckBox(m, text="Exibir mensagens recentes",
                        variable=v_recent).pack(anchor="w", padx=12)
        v_nodate = tk.BooleanVar(value=not s.show_datetime)
        ctk.CTkCheckBox(m, text="Ocultar pílulas de data (balões sempre têm hora)",
                        variable=v_nodate).pack(anchor="w", padx=12)
        ctk.CTkLabel(m, text="Ao receber mensagem:").pack(anchor="w", padx=12, pady=(6, 0))
        v_behav = tk.StringVar(value=s.incoming_behavior)
        ctk.CTkRadioButton(m, text="Minimizar mensagens recebidas na barra de tarefas",
                           variable=v_behav, value="minimize").pack(anchor="w", padx=24)
        ctk.CTkRadioButton(m, text="Definir as mensagens recebidas em primeiro-plano",
                           variable=v_behav, value="foreground").pack(anchor="w", padx=24)
        v_keep = tk.BooleanVar(value=s.keep_focus)
        ctk.CTkCheckBox(m, text="Manter foco do teclado na conversa",
                        variable=v_keep).pack(anchor="w", padx=12)
        v_toast = tk.BooleanVar(value=s.toast_enabled)
        ctk.CTkCheckBox(m, text="Notificações do sistema (toast no Windows 10/11)",
                        variable=v_toast).pack(anchor="w", padx=12)
        ctk.CTkLabel(m, text="Tamanho da Fonte",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 0))
        v_font = tk.StringVar(value=str(chatview.font_px(s.font_size)))
        ff = ctk.CTkFrame(m, fg_color="transparent")
        ff.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ff, text="Tamanho (px):").pack(side="left")
        font_entry = ctk.CTkEntry(ff, textvariable=v_font, width=70)
        font_entry.pack(side="left", padx=(6, 8))
        ctk.CTkLabel(ff, text="8 a 32 px", text_color="gray").pack(side="left")
        ctk.CTkLabel(m, text="Visualização:").pack(anchor="w", padx=12)
        preview = ctk.CTkLabel(m, text="Exemplo de Texto", fg_color=("gray85", "gray30"))
        preview.pack(fill="x", padx=12, pady=2)
        preview.configure(font=("TkDefaultFont", chatview.font_px(s.font_size)))

        def _preview_font(_event=None) -> None:
            preview.configure(
                font=("TkDefaultFont", chatview.font_px(v_font.get())))

        font_entry.bind("<KeyRelease>", _preview_font, add="+")

        # -- aba Transferência de Arquivo --
        nb.add("Transferência")
        t = nb.tab("Transferência")
        ctk.CTkLabel(t, text="Aceitação de Arquivo",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=4)
        accept = tk.StringVar(value=s.file_accept)
        ctk.CTkRadioButton(t, text="Iniciar download automaticamente",
                           variable=accept, value="auto").pack(anchor="w", padx=12)
        ctk.CTkRadioButton(t, text="Perguntar antes (primeira vez por remetente)",
                           variable=accept, value="ask").pack(anchor="w", padx=12)
        ctk.CTkLabel(t, text="Localização dos Arquivos de Entrada",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        inbox_var = tk.StringVar(value=s.inbox_dir)
        fi = ctk.CTkFrame(t, fg_color="transparent")
        fi.pack(fill="x", padx=8)
        ctk.CTkEntry(fi, textvariable=inbox_var).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fi, text="...", width=40,
                      command=lambda: inbox_var.set(
                          filedialog.askdirectory(parent=win) or inbox_var.get())).pack(side="left", padx=4)

        # -- aba Log --
        nb.add("Log")
        lg = nb.tab("Log")
        log_on = tk.BooleanVar(value=s.log_enabled)
        ctk.CTkCheckBox(lg, text="Habilitar log das mensagens",
                        variable=log_on).pack(anchor="w", padx=8, pady=4)
        ctk.CTkLabel(lg, text="Arquivos de Log",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8)
        log_mode = tk.StringVar(value=s.log_mode)
        ctk.CTkRadioButton(lg, text="Um arquivo de log", variable=log_mode,
                           value="single").pack(anchor="w", padx=12)
        ctk.CTkRadioButton(lg, text="Um arquivo por usuário", variable=log_mode,
                           value="per_user").pack(anchor="w", padx=12)
        log_sub = tk.BooleanVar(value=s.log_user_subdir)
        ctk.CTkCheckBox(lg, text="Criar subpasta por usuário",
                        variable=log_sub).pack(anchor="w", padx=28)
        ctk.CTkLabel(lg, text="Pasta dos logs (vazio = padrão)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
        logdir_var = tk.StringVar(value=s.log_dir)
        fl = ctk.CTkFrame(lg, fg_color="transparent")
        fl.pack(fill="x", padx=8)
        ctk.CTkEntry(fl, textvariable=logdir_var).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fl, text="...", width=40,
                      command=lambda: logdir_var.set(
                          filedialog.askdirectory(parent=win) or logdir_var.get())).pack(side="left", padx=4)
        ctk.CTkLabel(lg, text="Erros do aplicativo",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(10, 0))
        ctk.CTkLabel(lg, text="Falhas internas são gravadas em logs\\crash.log "
                              "(com data, hora e traceback) para análise.",
                     wraplength=430, justify="left", text_color="gray").pack(
            anchor="w", padx=12)
        ctk.CTkButton(lg, text="Abrir pasta do log de erros", width=200,
                      command=self._open_crash_folder).pack(anchor="w", padx=12, pady=4)

        # -- aba Eventos de Som --
        nb.add("Sons")
        snd = nb.tab("Sons")
        master = tk.BooleanVar(value=s.sounds_enabled)
        ctk.CTkCheckBox(snd, text="Tocar sons", variable=master).pack(anchor="w", padx=8, pady=4)
        ctk.CTkLabel(snd, text="Lista de Eventos de Som",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8)
        v_msg = tk.BooleanVar(value=s.snd_message)
        v_bcast = tk.BooleanVar(value=s.snd_broadcast)
        v_on = tk.BooleanVar(value=s.snd_user_online)
        v_file = tk.BooleanVar(value=s.snd_file)
        ctk.CTkCheckBox(snd, text="Mensagem recebida", variable=v_msg).pack(anchor="w", padx=12)
        ctk.CTkCheckBox(snd, text="Broadcast recebido", variable=v_bcast).pack(anchor="w", padx=12)
        ctk.CTkCheckBox(snd, text="Usuário está online", variable=v_on).pack(anchor="w", padx=12)
        ctk.CTkCheckBox(snd, text="Arquivo recebido", variable=v_file).pack(anchor="w", padx=12)
        v_mode = tk.StringVar(value=s.snd_msg_mode)
        ctk.CTkRadioButton(snd, text="Tocar sempre que a mensagem chegar",
                           variable=v_mode, value="always").pack(anchor="w", padx=12)
        ctk.CTkRadioButton(snd, text="Somente quando a conversa estiver em segundo plano",
                           variable=v_mode, value="background").pack(anchor="w", padx=12)
        v_rep = tk.BooleanVar(value=s.snd_repeat)
        v_repsec = tk.StringVar(value=str(s.snd_repeat_sec))
        fr = ctk.CTkFrame(snd, fg_color="transparent")
        fr.pack(fill="x", padx=12)
        ctk.CTkCheckBox(fr, text="Repetir som a cada", variable=v_rep).pack(side="left")
        ctk.CTkEntry(fr, textvariable=v_repsec, width=40).pack(side="left", padx=4)
        ctk.CTkLabel(fr, text="segundos até a conversa ficar ativa").pack(side="left")

        # -- aba Atalhos --
        nb.add("Atalhos")
        at = nb.tab("Atalhos")
        ctk.CTkLabel(at, text="Mensagens e Conversas",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=4)
        ctk.CTkLabel(at, text="Enviar mensagens usando:").pack(anchor="w", padx=12)
        v_send = tk.StringVar(value=s.send_key)
        ctk.CTkRadioButton(at, text="Enter", variable=v_send,
                           value="enter").pack(anchor="w", padx=24)
        ctk.CTkRadioButton(at, text="Ctrl + Enter", variable=v_send,
                           value="ctrl_enter").pack(anchor="w", padx=24)
        ctk.CTkLabel(at, text="Janela Principal",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 0))
        ctk.CTkLabel(at, text="Trazer o programa para a área de trabalho:").pack(anchor="w", padx=12)
        v_hot = tk.StringVar(value=s.bring_hotkey)
        ctk.CTkEntry(at, textvariable=v_hot, width=200).pack(anchor="w", padx=24, pady=2)
        ctk.CTkLabel(at, text="Ex: Ctrl + Shift + S (vale com o programa aberto)",
                     text_color="gray").pack(anchor="w", padx=24)

        def _intvar(var: tk.StringVar, default: int) -> int:
            try:
                return max(1, int(var.get()))
            except (TypeError, ValueError):
                return default

        def ok() -> None:
            s.away_after_min = _intvar(away, 10)
            s.hide_offline = hide.get()
            s.file_accept = accept.get()
            s.inbox_dir = inbox_var.get().strip() or "inbox"
            s.log_enabled = log_on.get()
            s.log_mode = log_mode.get()
            s.log_user_subdir = log_sub.get()
            s.log_dir = logdir_var.get().strip()
            s.sounds_enabled = master.get()
            s.snd_message = v_msg.get()
            s.snd_broadcast = v_bcast.get()
            s.snd_user_online = v_on.get()
            s.snd_file = v_file.get()
            s.snd_msg_mode = v_mode.get()
            s.snd_repeat = v_rep.get()
            s.snd_repeat_sec = _intvar(v_repsec, 5)
            s.send_key = v_send.get()
            if sfx.parse_hotkey(v_hot.get().strip() or s.bring_hotkey):
                s.bring_hotkey = v_hot.get().strip()
            s.show_recent = v_recent.get()
            s.show_datetime = not v_nodate.get()
            s.incoming_behavior = v_behav.get()
            s.keep_focus = v_keep.get()
            s.toast_enabled = v_toast.get()
            try:
                font_px = int(v_font.get().strip())
            except (TypeError, ValueError):
                messagebox.showwarning(
                    "Tamanho da Fonte",
                    "Digite um número inteiro entre 8 e 32 px.",
                    parent=win)
                font_entry.focus_set()
                return
            if not chatview.MIN_FONT_PX <= font_px <= chatview.MAX_FONT_PX:
                messagebox.showwarning(
                    "Tamanho da Fonte",
                    "Digite um valor entre 8 e 32 px.",
                    parent=win)
                font_entry.focus_set()
                return
            s.font_size = font_px
            s.autostart = auto.get()
            s.theme = v_theme.get() if v_theme.get() in ("Light", "Dark", "System") else "Light"
            try:
                if s.autostart:
                    autostart.enable()
                else:
                    autostart.disable()
            except OSError as e:
                messagebox.showwarning("Autostart", str(e), parent=win)
            profile.save(self.profile, s)
            self.file_server.set_inbox(s.inbox_dir)
            self._apply_bring_hotkey()
            for w in list(self.chat_windows.values()):
                if w.win.winfo_exists():
                    w.apply_font()
            for w in list(self.group_windows.values()):
                if w.win.winfo_exists():
                    w.apply_font()
            self.refresh()
            win.destroy()
        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bot, text="OK", width=100, command=ok).pack(side="right", padx=8)
        ctk.CTkButton(bot, text="Cancelar", width=100,
                      command=win.destroy).pack(side="right")

    def groups_dialog(self, parent) -> None:
        """Configurações dos Grupos (link da tela Geral): apelido + ocultar."""
        raw = ({str(i.get("dept") or "Geral") for i in self.disc.get_roster().values()}
               | set(self.settings.group_aliases)
               | set(self.settings.custom_groups)
               | set(self.settings.peer_groups.values()))
        depts = sorted("Geral" if d == "General" else d for d in raw)
        win = ctk_dialog(parent, "Configurações dos Grupos", "480x340")
        ctk.CTkLabel(win, text="Grupo original -> nome exibido (vazio = original):").pack(
            anchor="w", padx=8, pady=4)
        body = ctk.CTkScrollableFrame(win)
        body.pack(fill="both", expand=True, padx=8)
        alias_vars: dict[str, tk.StringVar] = {}
        hide_vars: dict[str, tk.BooleanVar] = {}
        for dept in depts or ["Geral"]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=dept, width=150, anchor="w").pack(side="left")
            v = tk.StringVar(value=self.settings.group_aliases.get(dept, ""))
            ctk.CTkEntry(row, textvariable=v, width=150).pack(side="left", padx=4)
            alias_vars[dept] = v
            h = tk.BooleanVar(value=dept in self.settings.hidden_groups)
            ctk.CTkCheckBox(row, text="Ocultar", variable=h).pack(side="left")
            hide_vars[dept] = h

        def ok() -> None:
            self.settings.group_aliases = {d: v.get().strip() for d, v in alias_vars.items()
                                           if v.get().strip() and v.get().strip() != d}
            self.settings.hidden_groups = [d for d, h in hide_vars.items() if h.get()]
            profile.save(self.profile, self.settings)
            self.refresh()
            win.destroy()

        def reset() -> None:
            self.settings.group_aliases = {}
            self.settings.hidden_groups = []
            profile.save(self.profile, self.settings)
            self.refresh()
            win.destroy()
        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(bot, text="Restaurar padrão", width=140,
                      command=reset).pack(side="left")
        ctk.CTkButton(bot, text="OK", width=90, command=ok).pack(side="right")
        ctk.CTkButton(bot, text="Cancelar", width=90,
                      command=win.destroy).pack(side="right", padx=4)

    def mass_dialog(self) -> None:
        """Enviar Mensagem em Massa com checkboxes por grupo (tela clássica)."""
        groups = roster.group_peers(self.disc.get_roster(), hide_offline=True,
                                    aliases=self.settings.group_aliases,
                                    hidden=self.settings.hidden_groups,
                                    overrides=self.settings.peer_groups,
                                    custom=self.settings.custom_groups)

        def send(ips: list[str], text: str) -> dict[str, str]:
            res = chat.send_broadcast(
                ips, text, from_name=self.profile.effective_display(),
                from_user=config.my_user(), key=self.key)
            for ip, st in res.items():
                if st == "ok":
                    self.store.add_message(f"mass-{time.time()}-{ip}", ip, "out", text)
                    logger.log_message(self.settings, self.peer_label(ip), "out", text)
            return res

        if not groups:
            messagebox.showinfo("Broadcast", "Nenhum usuário online.")
            return
        mass.open_mass_dialog(self.root, groups, send)

    def open_history(self, select_peer: str = "") -> None:
        """Ver Histórico de Mensagens (atalho da principal / botão da conversa)."""
        roster_now = self.disc.get_roster()

        def label_of(peer: str) -> str:
            info = roster_now.get(peer)
            return roster.label_of(info) if info else peer

        history_view.HistoryWindow(self.root, self.store, label_of,
                                   select_peer=select_peer)

    def about_dialog(self) -> None:
        """Ajuda e Sobre (atalho ❓ da principal)."""
        win = ctk_dialog(self.root, f"Sobre {config.APP_NAME}", "380x570")
        try:
            from PIL import Image
            ico = config.asset_path("app.ico")
            if ico:
                img = Image.open(ico)
                img.thumbnail((64, 64))
                from customtkinter import CTkImage as _CI
                photo = _CI(img, size=(64, 64))
                logo = ctk.CTkLabel(win, text="", image=photo)
                logo.pack(pady=(12, 0))
                logo.image = photo  # evita GC
            else:
                raise FileNotFoundError
        except Exception:
            ctk.CTkLabel(win, text="💬", font=ctk.CTkFont(size=44)).pack(pady=(12, 0))
        ctk.CTkLabel(win, text=config.APP_NAME,
                     font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(win, text=f"Versão {config.APP_VERSION}").pack()
        ctk.CTkLabel(win, text="Mensageiro corporativo P2P (rede local / VPN).",
                     text_color="gray").pack(pady=(0, 6))
        ctk.CTkLabel(win, text=("\"Todo aquele, pois, que escuta estas minhas palavras, "
                                "e as pratica, assemelhá-lo-ei ao homem prudente, "
                                "que edificou a sua casa sobre a rocha.\""),
                     wraplength=330, justify="center",
                     font=ctk.CTkFont(slant="italic")).pack(padx=12)
        ctk.CTkLabel(win, text="Mateus 7, 24", text_color="gray",
                     font=ctk.CTkFont(weight="bold")).pack(pady=(2, 6))
        ctk.CTkLabel(win, text="Suporte",
                     font=ctk.CTkFont(weight="bold")).pack()
        ctk.CTkLabel(win, text="Eder Silva").pack()
        ctk.CTkLabel(win, text="+55 (62) 98406-8103").pack()

        def _open(url: str) -> None:
            try:
                os.startfile(url)  # type: ignore[attr-defined]
            except OSError:
                pass
        mail = ctk.CTkLabel(win, text="eder.gyn@gmail.com", text_color="blue",
                            cursor="hand2")
        mail.pack()
        mail.bind("<Button-1>", lambda _e: _open("mailto:eder.gyn@gmail.com"))
        site = ctk.CTkLabel(win, text="www.edersilva.net", text_color="blue",
                            cursor="hand2")
        site.pack()
        site.bind("<Button-1>", lambda _e: _open("https://www.edersilva.net"))
        github = ctk.CTkLabel(win, text="github.com/edersilvago/lan-messenger",
                              text_color="blue", cursor="hand2")
        github.pack()
        github.bind("<Button-1>", lambda _e: _open(GITHUB_URL))
        ctk.CTkLabel(win, text="Copyright © 2026. Uso interno.",
                     text_color="gray").pack(pady=(6, 0))
        bot = ctk.CTkFrame(win, fg_color="transparent")
        bot.pack(pady=10)
        ctk.CTkButton(bot, text="Ajuda", width=90,
                      command=lambda: self.help_dialog(win)).pack(side="left", padx=4)
        ctk.CTkButton(bot, text="OK", width=90,
                      command=win.destroy).pack(side="left", padx=4)

    def help_dialog(self, parent) -> None:
        """Ajuda completa (guia de uso e funcionalidades)."""
        win = ctk_dialog(self.root, "Ajuda", "600x560", resizable=(True, True))
        txt = ctk.CTkTextbox(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", HELP_TEXT)
        txt.configure(state="disabled")
        ctk.CTkButton(win, text="Fechar", width=100,
                      command=win.destroy).pack(pady=6)


def main() -> None:
    root = make_root()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
