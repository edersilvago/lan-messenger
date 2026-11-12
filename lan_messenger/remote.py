"""Integrações externas: ping via CMD, AnyDesk e RustDesk (sem dependências)."""
from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess

PING_COUNT = 5

ANYDESK_NAMES = ("AnyDesk", "anydesk")
ANYDESK_PATHS = (
    r"%ProgramFiles(x86)%\AnyDesk\AnyDesk.exe",
    r"%ProgramFiles%\AnyDesk\AnyDesk.exe",
)
RUSTDESK_NAMES = ("RustDesk", "rustdesk")
RUSTDESK_PATHS = (
    r"%ProgramFiles%\RustDesk\RustDesk.exe",
    r"%ProgramFiles(x86)%\RustDesk\RustDesk.exe",
)


def valid_ip(s: str) -> bool:
    try:
        ipaddress.ip_address((s or "").strip())
        return True
    except ValueError:
        return False


def open_cmd_ping(ip: str, count: int = PING_COUNT) -> None:
    """Abre o CMD com N disparos de ping. Valida antes (anti-injeção)."""
    ip = (ip or "").strip()
    if not valid_ip(ip):
        raise ValueError(f"IP inválido: {ip!r}")
    n = max(1, min(int(count), 50))
    subprocess.Popen(["cmd", "/c", "start", f"Ping - {ip}",
                      "cmd", "/k", f"ping -n {n} {ip}"])


def _resolve(explicit: str | None, names: tuple[str, ...], paths: tuple[str, ...]) -> str | None:
    if explicit and os.path.isfile(explicit):
        return explicit
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for raw in paths:
        cand = os.path.expandvars(raw)
        if os.path.isfile(cand):
            return cand
    return None


def find_anydesk(exe: str | None = None) -> str | None:
    return _resolve(exe, ANYDESK_NAMES, ANYDESK_PATHS)


def find_rustdesk(exe: str | None = None) -> str | None:
    return _resolve(exe, RUSTDESK_NAMES, RUSTDESK_PATHS)


def clean_id(s: str) -> str:
    return " ".join((s or "").split())


def _digits_only(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _run_hidden(args: list[str], timeout: float = 15.0) -> str:
    """Executa oculto (sem console) e retorna o stdout; '' em falha."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, creationflags=0x08000000,  # CREATE_NO_WINDOW
                              startupinfo=si)
        return (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _conf_value(path: str, key: str) -> str:
    """Lê 'chave=valor' (AnyDesk) ou 'chave = valor' (TOML do RustDesk)."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip("'\"")
    except OSError:
        pass
    return ""


def get_anydesk_id(exe: str | None = None) -> str:
    """Descobre o ID do AnyDesk desta máquina, sem o usuário informar.

    Ordem: `AnyDesk.exe --get-id` (oficial) -> service.conf (ad.anynet.id).
    Retorna '' se o AnyDesk não estiver instalado.
    """
    prog = _resolve(exe, ANYDESK_NAMES, ANYDESK_PATHS)
    if prog:
        digits = _digits_only(_run_hidden([prog, "--get-id"]))
        if len(digits) >= 9:
            return digits
    for raw in (r"%ProgramData%\AnyDesk\service.conf",
                r"%APPDATA%\AnyDesk\service.conf"):
        val = _conf_value(os.path.expandvars(raw), "ad.anynet.id")
        if val.isdigit():
            return val
    return ""


def get_rustdesk_id(exe: str | None = None) -> str:
    """Descobre o ID do RustDesk desta máquina, sem o usuário informar.

    Ordem: `rustdesk.exe --get-id` -> RustDesk.toml (id = '...').
    Retorna '' se o RustDesk não estiver instalado.
    """
    prog = _resolve(exe, RUSTDESK_NAMES, RUSTDESK_PATHS)
    if prog:
        digits = _digits_only(_run_hidden([prog, "--get-id"]))
        if len(digits) >= 6:
            return digits
    for raw in (r"%APPDATA%\RustDesk\RustDesk.toml",
                r"%APPDATA%\RustDesk\config\RustDesk.toml"):
        val = _conf_value(os.path.expandvars(raw), "id")
        if val.isdigit():
            return val
    return ""


def connect_anydesk(id_: str, exe: str | None = None) -> str:
    """Abre o AnyDesk conectando no ID. Retorna o comando usado."""
    target = clean_id(id_)
    if not target:
        raise ValueError("ID AnyDesk vazio.")
    prog = _resolve(exe, ANYDESK_NAMES, ANYDESK_PATHS)
    if prog is None:
        raise OSError("AnyDesk não encontrado (instale ou ajuste o PATH).")
    subprocess.Popen([prog, target])
    return f"{prog} {target}"


def connect_rustdesk(id_: str, exe: str | None = None) -> str:
    """Abre o RustDesk com --connect <id>. Retorna o comando usado."""
    target = clean_id(id_)
    if not target:
        raise ValueError("ID RustDesk vazio.")
    prog = _resolve(exe, RUSTDESK_NAMES, RUSTDESK_PATHS)
    if prog is None:
        raise OSError("RustDesk não encontrado (instale ou ajuste o PATH).")
    subprocess.Popen([prog, "--connect", target])
    return f"{prog} --connect {target}"
