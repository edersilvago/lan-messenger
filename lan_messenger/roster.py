"""Agrupamento da lista de usuários por departamento (janela principal)."""
from __future__ import annotations

DEFAULT_DEPT = "Geral"
LEGACY_DEPT = "General"  # peers antigos anunciam "General" -> exibido como Geral


def group_peers(peers: dict[str, dict], hide_offline: bool = False,
                aliases: dict[str, str] | None = None,
                hidden: list[str] | tuple[str, ...] = (),
                overrides: dict[str, str] | None = None,
                custom: list[str] | tuple[str, ...] = ()) -> dict[str, list[tuple[str, dict]]]:
    """peers: {ip: {display|name, dept, status, ...}} -> {grupo: [(ip, info)]}.

    - Grupo = dept ou 'Geral' (padrão).
    - overrides: peer_key -> dept (Mover Usuário para...); custom: grupos
      extras (Adicionar Novo Grupo), exibidos mesmo vazios.
    - aliases renomeia grupos (Configurações dos Grupos); hidden oculta.
    - Grupos e usuários ordenados alfabeticamente (case-insensitive).
    - hide_offline=True remove status == 'offline'.
    """
    aliases = aliases or {}
    overrides = overrides or {}
    hidden_set = set(hidden or [])
    groups: dict[str, list[tuple[str, dict]]] = {}
    for ip, info in peers.items():
        status = str(info.get("status", "online"))
        if hide_offline and status == "offline":
            continue
        dept = str(info.get("dept") or info.get("department") or DEFAULT_DEPT).strip() or DEFAULT_DEPT
        if dept == LEGACY_DEPT:
            dept = DEFAULT_DEPT
        dept = overrides.get(peer_key(info), dept)
        if dept in hidden_set:
            continue
        dept = aliases.get(dept, dept)
        groups.setdefault(dept, []).append((ip, info))
    for name in list(custom or []) + list(aliases.values()):
        label = aliases.get(name, name)
        if label not in hidden_set:
            groups.setdefault(label, [])
    for members in groups.values():
        members.sort(key=lambda t: str(t[1].get("display") or t[1].get("name", "?")).lower())
    return dict(sorted(groups.items(), key=lambda kv: kv[0].lower()))


def order_labels(labels: list[str], order: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Ordem manual (Mover p/ Cima/Baixo); fora da lista, alfabético no fim."""
    rank = {name: i for i, name in enumerate(order or [])}
    return sorted(labels, key=lambda n: (rank.get(n, len(rank) + 1), n.lower()))


def label_of(info: dict) -> str:
    return str(info.get("display") or info.get("name") or "?")


def peer_key(info: dict) -> str:
    """Identidade estável p/ mover usuário de grupo (independe do IP/DHCP)."""
    return f"{info.get('user', '?')}|{info.get('name', '?')}"


STATUS_ICON = {"online": "●", "away": "●", "busy": "●", "offline": "○"}
