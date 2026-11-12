"""Config central do LAN Messenger P2P (MVP)."""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

UDP_DISCOVERY_PORT = int(os.getenv("LAN_UDP_PORT", "50000"))
TCP_CHAT_PORT = int(os.getenv("LAN_CHAT_PORT", "50001"))
TCP_FILE_PORT = int(os.getenv("LAN_FILE_PORT", "50002"))

APP_NAME = "LAN Messenger"
APP_VERSION = "1.24"


def app_data_dir() -> Path:
    """Pasta gravável: %APPDATA%\\LANMessenger no .exe; pasta do pacote no dev."""
    if getattr(sys, "frozen", False):
        base = os.getenv("APPDATA") or str(Path.home())
        d = Path(base) / "LANMessenger"
    else:
        d = Path(__file__).parent
    d.mkdir(parents=True, exist_ok=True)
    return d


APP_DATA = app_data_dir()


def asset_path(name: str) -> str | None:
    """Localiza um asset: dir do .exe > bundle > pacote dev (com/sem assets/)."""
    cands: list[Path] = []
    if getattr(sys, "frozen", False):
        cands += [Path(sys.executable).parent / name,
                  Path(sys.executable).parent / "assets" / name]
        base = getattr(sys, "_MEIPASS", None)
        if base:
            cands += [Path(base) / "lan_messenger" / name,
                      Path(base) / "lan_messenger" / "assets" / name]
    cands += [Path(__file__).parent / "assets" / name,
              Path(__file__).parent / name]
    for c in cands:
        if c.is_file():
            return str(c)
    return None

BEACON_INTERVAL = 4.0      # segundos entre beacons (presença rápida na VPN)
PEER_TIMEOUT = 60.0        # sem beacon => offline (tolera perda UDP na VPN)
STALE_WARN_AGE = 20.0      # sem beacon há +20s => "sinal fraco" (avisa, não some)
TCP_CONFIRM_TIMEOUT = 1.5  # checagem TCP rápida antes de enviar p/ par duvidoso
BROADCAST_ADDR = "<broadcast>"
CHUNK_SIZE = 64 * 1024     # 64KB p/ arquivos
ACK_TIMEOUT = 8.0          # maior p/ atravessar VPN
HELLO_ROUNDS = 3           # beacons rápidos ao abrir (encontro imediato)
BEACON_PACE_EVERY = 24     # pacotes unicast por rajada (evita flood na VPN)
BEACON_PACE_PAUSE = 0.005  # pausa entre rajadas (espalha o envio)

NETWORKS_FILE = str(__import__("pathlib").Path(__file__).with_name("networks.json"))
PEERS_CACHE_FILE = str(APP_DATA / "peers_cache.json")
USER_NETWORKS_FILE = str(APP_DATA / "networks.json")

ENCODING = "utf-8"

def my_hostname() -> str:
    return socket.gethostname()

def my_user() -> str:
    return os.getenv("USERNAME") or os.getenv("USER") or "user"

def my_ips() -> list[str]:
    """Lista IPs locais (não-loopback) p/ exibir. Best-effort."""
    ips = set()
    try:
        ips.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    # truque UDP p/ descobrir IP da rota default (não envia nada)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith("127."))
