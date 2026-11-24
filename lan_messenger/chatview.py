"""Apresentação da conversa (tela Mensagens): fontes e linhas. Sem Tk (testável)."""
from __future__ import annotations

import re
from datetime import datetime

FONT_SIZES = {"normal": 9, "large": 11, "xlarge": 13}
MIN_FONT_PX = 8
MAX_FONT_PX = 32
DEFAULT_CHAT_GEOMETRY = "650x620"
MIN_CHAT_WIDTH = 620
MIN_CHAT_HEIGHT = 560

_GEOM = re.compile(r"^\d+x\d+([+-]\d+[+-]\d+)?$")


def valid_geometry(s: str) -> bool:
    """'480x420' ou '300x620+10+10'. Recusa resto (não restaura lixo)."""
    return bool(_GEOM.match((s or "").strip()))


def geometry_size(s: str) -> tuple[int, int]:
    """Retorna (largura, altura) de uma geometria Tk; (0, 0) se inválida."""
    if not valid_geometry(s):
        return 0, 0
    wh = (s or "").split("+", 1)[0].split("-", 1)[0]
    try:
        w, h = wh.split("x", 1)
        return int(w), int(h)
    except (TypeError, ValueError):
        return 0, 0


def conversation_geometry(saved: str) -> str:
    """Geometria inicial das conversas: nunca menor que o layout completo."""
    w, h = geometry_size(saved)
    if w >= MIN_CHAT_WIDTH and h >= MIN_CHAT_HEIGHT:
        return saved
    return DEFAULT_CHAT_GEOMETRY


def font_px(font_size: str | int) -> int:
    """Converte preferência antiga ou px digitado; limita a 8–32 px."""
    if str(font_size) in FONT_SIZES:
        return FONT_SIZES[str(font_size)]
    try:
        px = int(str(font_size).strip())
    except (TypeError, ValueError):
        px = FONT_SIZES["large"]
    return max(MIN_FONT_PX, min(MAX_FONT_PX, px))


def format_line(direction: str, who: str, text: str, ts: str = "",
                show_datetime: bool = True) -> str:
    """'[ts] quem: texto' ou 'quem: texto' (tela Mensagens: data/hora)."""
    head = f"[{ts}] {who}" if (show_datetime and ts) else who
    return f"{head}: {text}"


def invite_text(inviter: str) -> str:
    return f"[Convite] {inviter} convidou você para uma conversa."


MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Formatos reais de carimbo: ao vivo "%d/%m/%Y - %H:%M:%S",
# histórico SQLite "YYYY-MM-DD HH:MM:SS".
_TS_FORMATS = ("%d/%m/%Y - %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_ts(ts: str):
    """datetime de um carimbo conhecido; None se irreconhecível."""
    s = (ts or "").strip()
    if not s:
        return None
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def bubble_time(ts: str) -> str:
    """"HH:MM:SS" p/ dentro do balão; "" se irreconhecível."""
    dt = parse_ts(ts)
    return dt.strftime("%H:%M:%S") if dt else ""


def date_label(ts: str) -> str:
    """"14 de outubro de 2026" p/ separador de data; "" se irreconhecível."""
    dt = parse_ts(ts)
    if not dt:
        return ""
    return f"{dt.day} de {MESES_PT[dt.month - 1]} de {dt.year}"


def format_size(num_bytes: float) -> str:
    """"1,2 MB" / "589 KB" (pt-BR) p/ cartão de anexo."""
    try:
        n = float(num_bytes)
    except (TypeError, ValueError):
        return "-"
    if n < 0:
        return "-"
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):,.1f} MB".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{n / 1024:,.0f} KB".replace(",", ".")


_URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)
# Ordem importa: combinações mais longas primeiro (v1.39).
EMOTICON_MAP: tuple[tuple[str, str], ...] = (
    (":'(", "😢"),
    (":'-(", "😢"),
    (":-)", "😊"), (":)", "😊"),
    (":-(", "😞"), (":(", "😞"),
    (":-D", "😃"), (":D", "😃"), (":-d", "😃"), (":d", "😃"),
    (";-)", "😉"), (";)", "😉"),
    (":-P", "😛"), (":P", "😛"), (":-p", "😛"), (":p", "😛"),
    (":-O", "😮"), (":O", "😮"), (":-o", "😮"), (":o", "😮"),
    (":-/", "😕"), (":/", "😕"),
    (":-|", "😐"), (":|", "😐"),
    ("<3", "❤️"),
    ("(y)", "👍"), ("(Y)", "👍"),
    ("(n)", "👎"), ("(N)", "👎"),
)


def translate_emoticons(text: str) -> str:
    """Converte atalhos de texto em emoji após envio (v1.39)."""
    raw = str(text or "")
    if not raw:
        return raw
    parts = []
    pos = 0
    for m in _URL_RE.finditer(raw):
        if m.start() > pos:
            parts.append(_replace_emoticons(raw[pos:m.start()]))
        parts.append(raw[m.start():m.end()])
        pos = m.end()
    if pos < len(raw):
        parts.append(_replace_emoticons(raw[pos:]))
    return "".join(parts)


def _replace_emoticons(text: str) -> str:
    for src, dst in EMOTICON_MAP:
        if src not in text:
            continue
        # início/espaço antes; fim/espaço/pontuação depois (evita falsos positivos)
        pattern = re.compile(r"(?<!\S)" + re.escape(src) + r"(?=\s|$|[.,!?;:\])}])")
        text = pattern.sub(dst, text)
    return text
