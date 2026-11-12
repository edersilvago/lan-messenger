"""CLI de demonstração: lista peers, envia msg/broadcast/arquivo.

Uso:
    python -m lan_messenger.app_cli --name MEU-PC
    python -m lan_messenger.app_cli --name MEU-PC --add-peer 192.168.1.20
    python -m lan_messenger.app_cli --name MEU-PC --range 10.0.0.1-10.0.0.254
Comandos: /list /msg IP texto /bcast texto /file IP caminho
          /ranges /addrange FAIXA /delrange FAIXA /hist /quit
Faixas (p/ VPN): mesmo conceito da tela Rede do Softros.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import chat, config, discovery, files
from .store import Store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=config.my_hostname())
    ap.add_argument("--user", default=config.my_user())
    ap.add_argument("--add-peer", action="append", default=[],
                    help="IP manual (rede sem broadcast ou teste local). Pode repetir.")
    ap.add_argument("--range", dest="ranges", action="append", default=[],
                    help="Faixa extra ex 10.0.0.1-10.0.0.254. Pode repetir.")
    ap.add_argument("--key", default="",
                    help="PSK base64 (mesma da tela Rede). Sem ela, tráfego em claro.")
    ap.add_argument("--inbox", default="inbox")
    args = ap.parse_args()

    from . import crypto as _crypto
    key = _crypto.parse_key(args.key) if args.key else None
    if args.key and key is None:
        ap.error("chave inválida (esperado base64 de 32 bytes)")

    store = Store()
    received: list[str] = []

    def on_msg(msg: dict, ip: str) -> None:
        line = f"\n[{msg.get('from_name', ip)}@{ip}] {msg.get('text', '')}"
        received.append(line)
        print(line)
        store.add_message(str(msg.get("id")), ip, "in", str(msg.get("text", "")))

    def on_file(header: dict, path: Path, ip: str = "") -> None:
        print(f"\n[arquivo recebido] {header.get('filename')} -> {path}")
        store.add_file(str(header.get("id")), str(header.get("from_name", "?")),
                       str(header.get("filename", "")), int(header.get("size", 0)), str(path))

    disc = discovery.Discovery(name=args.name, user=args.user).start()
    for spec in args.ranges:
        try:
            n = disc.add_range(spec)
            print(f"faixa {spec}: {n} IPs")
        except ValueError as e:
            print(f"faixa inválida {spec}: {e}")
    for ip in args.add_peer:
        disc.add_peer_manual(ip)
    chat.ChatServer(on_message=on_msg, key=key).start()
    files.FileServer(inbox=args.inbox, on_file=on_file, key=key).start()

    print(f"Eu: {args.name} ({args.user}) | IPs: {config.my_ips()}")
    print("Cripto: ON (PSK) 🔒" if key else "Cripto: OFF (em claro)")
    print(f"Portas UDP {config.UDP_DISCOVERY_PORT} / TCP chat {config.TCP_CHAT_PORT} / TCP file {config.TCP_FILE_PORT}")
    print(f"Faixas VPN: {disc.get_ranges() or '(nenhuma - só broadcast local)'}")
    print("Comandos: /list /msg IP texto /bcast texto /file IP caminho /ranges /addrange FAIXA /delrange FAIXA /hist /quit")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line == "/quit":
            break
        if line == "/list":
            peers = disc.get_peers()
            print(f"{len(peers)} peer(s):" if peers else "(nenhum peer ainda - aguarde beacon ou use --add-peer)")
            for ip, p in peers.items():
                print(f"  {ip}  {p['name']} ({p['user']}) [{p['status']}]")
        elif line.startswith("/msg "):
            parts = line.split(maxsplit=2)
            if len(parts) < 3:
                print("uso: /msg IP texto"); continue
            _, ip, text = parts
            try:
                mid = chat.send_message(ip, text, from_name=args.name, from_user=args.user,
                                        key=key)
                store.add_message(mid, ip, "out", text)
                print("enviado ok")
            except Exception as e:
                print(f"falha: {e}")
        elif line.startswith("/bcast "):
            text = line[len("/bcast "):]
            res = chat.send_broadcast(list(disc.get_peers()), text,
                                      from_name=args.name, from_user=args.user, key=key)
            for ip, st in res.items():
                print(f"  {ip}: {st}")
        elif line.startswith("/file "):
            parts = line.split(maxsplit=2)
            if len(parts) < 3:
                print("uso: /file IP caminho"); continue
            _, ip, fpath = parts
            try:
                fid = files.send_file(ip, fpath, from_name=args.name,
                                      on_progress=lambda n, d, t: print(f"\r{n}: {d}/{t}", end=""),
                                      key=key)
                print(f"\narquivo ok id={fid}")
            except Exception as e:
                print(f"\nfalha: {e}")
        elif line == "/ranges":
            for r in disc.get_ranges():
                print(f"  {r}")
            if not disc.get_ranges():
                print("(nenhuma faixa - só broadcast local)")
        elif line.startswith("/addrange "):
            spec = line[len("/addrange "):].strip()
            try:
                n = disc.add_range(spec)
                print(f"faixa {spec}: {n} IPs (salvo em networks.json)")
            except ValueError as e:
                print(f"inválida: {e}")
        elif line.startswith("/delrange "):
            spec = line[len("/delrange "):].strip()
            print("removida" if disc.del_range(spec) else "não encontrada")
        elif line == "/hist":
            for peer, direction, text, ts in store.recent_messages():
                print(f"[{ts}] {direction} {peer}: {text}")
        else:
            print("comando desconhecido")
    disc.stop()
    print("encerrado.")


if __name__ == "__main__":
    main()
