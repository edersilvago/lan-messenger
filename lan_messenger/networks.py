"""Faixas de broadcast dirigido p/ atravessar VPN/roteadores.

O broadcast limitado (<broadcast>/255.255.255.255) NÃO atravessa VPN.
Igual ao Softros (tela Rede -> Transmissão), aqui você cadastra faixas:
  "10.0.0.1-10.0.0.254", "192.168.30.1-192.168.30.254"

O Discovery envia beacon UDP unicast p/ cada IP da faixa + p/ o
broadcast dirigido (ex 192.168.30.255). O TCP de chat/arquivo já cruza
a VPN sozinho, desde que haja rota + firewall liberado.
"""
from __future__ import annotations

import ipaddress
import json
import socket
from pathlib import Path

MAX_IPS_PER_RANGE = 512  # protege contra /16 acidental (65k pacotes)

# Faixas de fábrica (usadas quando não há networks.json do usuário).
DEFAULT_RANGES = ["10.0.0.1-10.0.0.254", "192.168.30.1-192.168.30.254"]


def parse_range(spec: str) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]:
    spec = spec.strip()
    if "-" not in spec:
        # IP único: "10.0.0.5" == "10.0.0.5-10.0.0.5"
        ip = ipaddress.IPv4Address(spec)
        return ip, ip
    a, b = spec.split("-", 1)
    start, end = ipaddress.IPv4Address(a.strip()), ipaddress.IPv4Address(b.strip())
    if int(end) < int(start):
        raise ValueError(f"faixa invertida: {spec}")
    if int(end) - int(start) + 1 > MAX_IPS_PER_RANGE:
        raise ValueError(f"faixa grande demais (> {MAX_IPS_PER_RANGE} IPs): {spec} "
                         f"- quebre em faixas menores ou use IPs manuais")
    return start, end


def expand_range(spec: str) -> list[str]:
    """'10.0.0.1-10.0.0.3' -> ['10.0.0.1','10.0.0.2','10.0.0.3']."""
    start, end = parse_range(spec)
    return [str(ipaddress.IPv4Address(i)) for i in range(int(start), int(end) + 1)]


def directed_broadcast(spec: str) -> str | None:
    """'192.168.30.1-192.168.30.254' -> '192.168.30.255' (se mesmo /24)."""
    try:
        start, end = parse_range(spec)
    except ValueError:
        return None
    a, b = start.packed, end.packed
    if a[:3] == b[:3]:  # mesmo /24
        return f"{a[0]}.{a[1]}.{a[2]}.255"
    return None


def expand_all(ranges: list[str]) -> list[str]:
    """Todos os IPs unicast + broadcasts dirigidos, sem duplicar."""
    out: list[str] = []
    seen: set[str] = set()

    def add(ip: str) -> None:
        if ip not in seen:
            seen.add(ip)
            out.append(ip)

    for spec in ranges:
        db = directed_broadcast(spec)
        if db:
            add(db)
        try:
            for ip in expand_range(spec):
                add(ip)
        except ValueError:
            continue  # faixa inválida: ignora (GUI/CLI validam na entrada)
    return out


def load_ranges(path: str | Path, defaults: list[str] = ()) -> list[str]:
    p = Path(path)
    if not p.is_file():
        return list(defaults)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(x) for x in data]
        if isinstance(data, dict) and isinstance(data.get("ranges"), list):
            return [str(x) for x in data["ranges"]]
    except (ValueError, UnicodeDecodeError, OSError):
        pass
    return list(defaults)


def save_ranges(path: str | Path, ranges: list[str]) -> None:
    p = Path(path)
    p.write_text(json.dumps({"ranges": ranges}, indent=2), encoding="utf-8")


def tcp_ping(ip: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    """Testa TCP direto (chat/arquivo) sem discovery. Distingue 'sem rota/
    firewall' de 'discovery bloqueado'."""
    try:
        with socket.create_connection((ip.strip(), port), timeout=timeout):
            return True, "alcançável"
    except Exception as e:  # noqa: BLE001 - mensagem vira diagnóstico na tela
        return False, str(e) or "falha"
