"""Perfil do usuário + preferências (telas Geral e Informações do Usuário)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config


@dataclass
class Profile:
    display_name: str = ""
    first_name: str = ""
    last_name: str = ""
    department: str = "Geral"
    role: str = ""
    info: str = ""
    anydesk_id: str = ""
    rustdesk_id: str = ""

    def effective_display(self) -> str:
        return self.display_name.strip() or config.my_hostname()


@dataclass
class Settings:
    away_after_min: int = 10
    hide_offline: bool = False
    show_taskbar_when_minimized: bool = False
    language: str = "PortugueseBrazilian"
    auto_download_files: bool = True  # legado: mapeado p/ file_accept no load
    file_accept: str = "auto"         # "auto" | "ask" (tela Transferência)
    approved_senders: list = field(default_factory=list)  # sempre permitidos (modo ask)
    inbox_dir: str = field(default_factory=lambda: str(config.APP_DATA / "inbox"))
    log_enabled: bool = True
    log_mode: str = "single"          # "single" | "per_user" (tela Log)
    log_dir: str = ""                 # "" = pasta logs/ do pacote
    log_user_subdir: bool = False     # cria subpasta por usuário
    # -- Atalhos (tela Atalhos) --
    send_key: str = "enter"           # "enter" | "ctrl_enter"
    bring_hotkey: str = "Ctrl + Shift + S"  # traz janela principal p/ frente
    # -- Sons (tela Eventos de Som) --
    sounds_enabled: bool = False      # mestre "Tocar sons"
    snd_message: bool = True          # mensagem recebida
    snd_broadcast: bool = True        # broadcast recebido
    snd_msg_mode: str = "background"  # "always" | "background"
    snd_repeat: bool = False          # repete até a conversa ficar ativa
    snd_repeat_sec: int = 5
    snd_user_online: bool = True
    snd_file: bool = True
    # -- Segurança / inicialização --
    crypto_key: str = ""              # PSK base64 (tela Rede); "" = sem cripto
    autostart: bool = False           # iniciar com o Windows (HKCU Run)
    # -- Mensagens / Janela de Mensagem (tela Mensagens) --
    show_recent: bool = True          # exibir mensagens recentes ao abrir
    show_datetime: bool = True        # mostrar data/hora (desmarcado = "não mostrar")
    incoming_behavior: str = "foreground"  # "foreground" | "minimize"
    keep_focus: bool = False          # manter foco do teclado na conversa
    font_size: str = "large"          # "normal" | "large" | "xlarge"
    group_aliases: dict = field(default_factory=dict)  # dept -> apelido
    hidden_groups: list = field(default_factory=list)  # depts ocultos
    custom_groups: list = field(default_factory=list)  # Adicionar Novo Grupo
    peer_groups: dict = field(default_factory=dict)  # peer_key -> dept (Mover Usuário)
    group_order: list = field(default_factory=list)  # ordem manual dos grupos
    main_geometry: str = ""           # posição/tamanho da principal (WxH+X+Y)
    chat_geometry: str = "650x620"    # padrão das conversas
    theme: str = "Light"              # "Light" | "Dark" | "System" (Aparência)
    busy_msg: str = "Eu estou ocupado agora. Favor não me perturbar."
    away_msg: str = ("Eu estou ausente do meu computador. Favor deixar sua "
                     "mensagem e eu irei respondê-lo o mais breve possível "
                     "quando eu retornar.")

    def __post_init__(self) -> None:
        if self.away_after_min < 1:
            self.away_after_min = 1
        if self.send_key not in ("enter", "ctrl_enter"):
            self.send_key = "enter"
        if self.snd_msg_mode not in ("always", "background"):
            self.snd_msg_mode = "background"
        if self.snd_repeat_sec < 1:
            self.snd_repeat_sec = 5
        if self.incoming_behavior not in ("foreground", "minimize"):
            self.incoming_behavior = "foreground"
        if self.font_size not in ("normal", "large", "xlarge"):
            self.font_size = "large"
        if self.file_accept not in ("auto", "ask"):
            self.file_accept = "auto"
        if self.theme not in ("Light", "Dark", "System"):
            self.theme = "Light"
        if self.log_mode not in ("single", "per_user"):
            self.log_mode = "single"


def _paths(base: str | Path | None = None) -> tuple[Path, Path]:
    root = Path(base) if base else config.APP_DATA
    return root / "profile.json", root / "settings.json"


def load(base: str | Path | None = None) -> tuple[Profile, Settings]:
    pf, sf = _paths(base)
    profile = Profile()
    settings = Settings()
    try:
        if pf.is_file():
            d = json.loads(pf.read_text(encoding="utf-8"))
            for k in asdict(profile):
                if k in d and isinstance(d[k], str):
                    setattr(profile, k, d[k])
    except (ValueError, UnicodeDecodeError, OSError):
        pass
    try:
        if sf.is_file():
            d = json.loads(sf.read_text(encoding="utf-8"))
            for k in ("away_after_min", "hide_offline", "show_taskbar_when_minimized",
                      "language", "auto_download_files", "file_accept",
                      "approved_senders", "inbox_dir", "log_enabled",
                      "log_mode", "log_dir", "log_user_subdir",
                      "send_key", "bring_hotkey",
                      "sounds_enabled", "snd_message", "snd_broadcast",
                      "snd_msg_mode", "snd_repeat", "snd_repeat_sec",
                      "snd_user_online", "snd_file",
                      "crypto_key", "autostart",
                      "show_recent", "show_datetime", "incoming_behavior",
                      "keep_focus", "font_size",
                      "group_aliases", "hidden_groups",
                      "custom_groups", "peer_groups", "group_order",
                      "main_geometry", "chat_geometry",
                      "busy_msg", "away_msg", "theme"):
                if k in d:
                    setattr(settings, k, d[k])
            # compat: settings antigos só tinham auto_download_files
            if "file_accept" not in d and "auto_download_files" in d:
                settings.file_accept = "auto" if d["auto_download_files"] else "ask"
    except (ValueError, UnicodeDecodeError, OSError):
        pass
    return profile, settings


def save(profile: Profile, settings: Settings,
         base: str | Path | None = None) -> None:
    pf, sf = _paths(base)
    pf.write_text(json.dumps(asdict(profile), indent=2, ensure_ascii=False), encoding="utf-8")
    sf.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
