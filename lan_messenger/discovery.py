"""Discovery P2P via UDP (broadcast local + unicast dirigido p/ VPN)."""
from __future__ import annotations

import json
import socket
import threading
import time

from . import config, networks, protocol


class Discovery:
    """Anuncia presença e escuta beacons. Cruza VPN via faixas configuradas."""

    def __init__(self, name: str = "", user: str = "",
                 udp_port: int | None = None,
                 broadcast: str = config.BROADCAST_ADDR,
                 ranges: list[str] | None = None,
                 networks_file: str | None = None,
                 send_port: int | None = None,
                 display: str = "", dept: str = "Geral", role: str = "",
                 anydesk: str = "", rustdesk: str = "",
                 hw: dict[str, str] | None = None,
                 status_msg: str = "",
                 app_version: str = ""):
        self.name = name or config.my_hostname()
        self.user = user or config.my_user()
        self.udp_port = udp_port or config.UDP_DISCOVERY_PORT
        # porta de destino (padrão = mesma da escuta; diferente só em teste
        # com 2 instâncias no mesmo PC, que não podem dividir a porta no Windows)
        self.send_port = send_port or self.udp_port
        self.broadcast = broadcast
        self.networks_file = networks_file or config.USER_NETWORKS_FILE
        if ranges is None:
            ranges = networks.load_ranges(self.networks_file, networks.DEFAULT_RANGES)
        self._ranges: list[str] = list(ranges)
        self._targets: list[str] = networks.expand_all(self._ranges)
        self.status = "online"
        self.display = display or self.name
        self.dept = dept or "Geral"
        self.role = role or ""
        self.anydesk = anydesk or ""
        self.rustdesk = rustdesk or ""
        self.hw = hw or {}
        self.status_msg = status_msg or ""
        self.app_version = app_version or config.APP_VERSION
        self._peers: dict[str, dict] = {}  # ip -> info (online)
        self._known: dict[str, dict] = {}  # ip -> última info (p/ "ocultar offline")
        # -- diagnóstico (tela Rede) --
        self.bind_ok: bool | None = None   # None=não tentou, True/False
        self.bind_error: str = ""
        self.last_tx: float = 0.0          # último beacon enviado
        self.tx_count: int = 0
        self.tx_errors: int = 0
        self.last_rx: float = 0.0          # último beacon recebido
        self.last_rx_from: str = ""
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # -- API pública -------------------------------------------------
    def start(self) -> "Discovery":
        self._stop.clear()
        t1 = threading.Thread(target=self._beacon_loop, daemon=True, name="beacon")
        t2 = threading.Thread(target=self._listen_loop, daemon=True, name="listen")
        t3 = threading.Thread(target=self._reaper_loop, daemon=True, name="reaper")
        self._threads = [t1, t2, t3]
        for t in self._threads:
            t.start()
        # sonda imediata: pares respondem na hora (lista enche em ~1 RTT)
        threading.Thread(target=self._send_ping, daemon=True, name="ping").start()
        return self

    def stop(self) -> None:
        self._send_goodbye()
        self._stop.set()

    def ping_now(self) -> None:
        """Sonda imediata (botão Atualizar / refresh periódico). Não bloqueia."""
        threading.Thread(target=self._send_ping, daemon=True, name="ping-now").start()

    def peer_age(self, ip: str) -> float:
        """Segundos desde o último beacon do IP. inf se desconhecido."""
        with self._lock:
            info = self._peers.get(ip) or self._known.get(ip)
            if not info:
                return float("inf")
            try:
                ts = float(info.get("ts", 0))
            except (TypeError, ValueError):
                return float("inf")
            return float("inf") if ts <= 0 else time.time() - ts

    def is_stale(self, ip: str) -> bool:
        """Online mas sem beacon há +STALE_WARN_AGE: sinal fraco (VPN/UDP)."""
        with self._lock:
            info = self._peers.get(ip)
            if not info:
                return False
            try:
                return (time.time() - float(info.get("ts", 0))) > config.STALE_WARN_AGE
            except (TypeError, ValueError):
                return False

    def mark_unreachable(self, ip: str) -> None:
        """Falha de TCP ao enviar: marca offline na hora (não espera timeout)."""
        with self._lock:
            info = self._peers.pop(ip, None) or self._known.get(ip)
            if info:
                info = dict(info)
                info["status"] = "offline"
                self._known[ip] = info

    def local_beacon(self) -> dict:
        """Beacon desta máquina como dict (resposta ao hello TCP)."""
        with self._lock:
            hw = dict(self.hw)
            return protocol.make_beacon(
                self.name, self.user, self.status, self.display,
                self.dept, self.role, self.anydesk, self.rustdesk,
                hw.get("cpu", ""), hw.get("ram", ""), hw.get("ram_type", ""),
                hw.get("disk", ""), hw.get("os", ""), self.status_msg,
                self.app_version)

    def snapshot_known(self) -> dict[str, dict]:
        """Cópia dos já vistos (p/ varredura TCP de recuperação)."""
        with self._lock:
            return {ip: dict(info) for ip, info in self._known.items()}

    def stale_ips(self) -> list[str]:
        """Online sem beacon recente (candidatos ao hello TCP)."""
        with self._lock:
            now = time.time()
            out = []
            for ip, p in self._peers.items():
                if p.get("manual"):
                    continue
                try:
                    age = now - float(p.get("ts", 0))
                except (TypeError, ValueError):
                    age = float("inf")
                if age > config.STALE_WARN_AGE:
                    out.append(ip)
            return out

    def note_tcp_beacon(self, ip: str, obj: dict) -> bool:
        """Registra beacon vindo do hello TCP (UDP morto na VPN)."""
        if not isinstance(obj, dict) or obj.get("type") != "beacon":
            return False
        if self._is_self(obj, ip):
            return False
        with self._lock:
            self._peers[ip] = self._build_info(obj, via="tcp")
            self._known[ip] = dict(self._peers[ip])
            self.last_rx = time.time()
            self.last_rx_from = ip
        return True

    @staticmethod
    def _build_info(obj: dict, via: str) -> dict:
        return {
            "name": str(obj.get("name", "?")),
            "display": str(obj.get("display") or obj.get("name", "?")),
            "dept": str(obj.get("dept") or obj.get("department") or "Geral"),
            "role": str(obj.get("role", "")),
            "user": str(obj.get("user", "?")),
            "status": str(obj.get("status", "online")),
            "anydesk": str(obj.get("anydesk", "") or ""),
            "rustdesk": str(obj.get("rustdesk", "") or ""),
            "cpu": str(obj.get("cpu", "") or ""),
            "ram": str(obj.get("ram", "") or ""),
            "ram_type": str(obj.get("ram_type", "") or ""),
            "disk": str(obj.get("disk", "") or ""),
            "os": str(obj.get("os", "") or ""),
            "status_msg": str(obj.get("status_msg", "") or ""),
            "app_version": str(obj.get("app_version", "") or ""),
            "via": via,
            "ts": float(obj.get("ts", time.time())),
        }

    def save_peer_cache(self) -> None:
        """Grava colegas recentes (recuperação rápida após reiniciar)."""
        try:
            import json as _json
            with self._lock:
                data = {ip: dict(info) for ip, info in self._known.items()}
            data = dict(sorted(data.items())[:200])
            with open(config.PEERS_CACHE_FILE, "w", encoding="utf-8") as f:
                _json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

    def load_peer_cache(self) -> dict[str, dict]:
        """Colegas da última sessão (entram como offline até confirmar)."""
        try:
            import json as _json
            with open(config.PEERS_CACHE_FILE, encoding="utf-8") as f:
                data = _json.load(f)
            if not isinstance(data, dict):
                return {}
            return {str(ip): dict(info) for ip, info in data.items()
                    if isinstance(info, dict)}
        except (OSError, ValueError, UnicodeDecodeError):
            return {}

    def seed_known(self, cache: dict[str, dict]) -> None:
        """Semeia os já vistos como offline (somem do cinza ao confirmar)."""
        if not cache:
            return
        with self._lock:
            for ip, info in cache.items():
                if ip in self._peers or ip in self._known:
                    continue
                seeded = dict(info)
                seeded["status"] = "offline"
                seeded["ts"] = 0.0
                self._known[ip] = seeded
        """Falha de TCP ao enviar: marca offline na hora (não espera timeout)."""
        with self._lock:
            info = self._peers.pop(ip, None) or self._known.get(ip)
            if info:
                info = dict(info)
                info["status"] = "offline"
                self._known[ip] = info

    def _send_goodbye(self) -> None:
        """Aviso de saída: pares marcam offline na hora (sem esperar timeout)."""
        try:
            import json as _json
            import socket as _socket
            with self._lock:
                name, user = self.name, self.user
                display, dept, role = self.display, self.dept, self.role
                anydesk, rustdesk = self.anydesk, self.rustdesk
                hw = dict(self.hw)
            msg = _json.dumps(
                protocol.make_beacon(name, user, "offline", display, dept, role,
                                     anydesk, rustdesk,
                                     hw.get("cpu", ""), hw.get("ram", ""),
                                     hw.get("ram_type", ""), hw.get("disk", ""),
                                     hw.get("os", ""))
            ).encode(config.ENCODING)
            sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            try:
                sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_BROADCAST, 1)
                try:
                    sock.sendto(msg, (self.broadcast, self.send_port))
                except OSError:
                    pass
                for ip in self._targets_snapshot():
                    try:
                        sock.sendto(msg, (ip, self.send_port))
                    except OSError:
                        continue
            finally:
                try:
                    sock.close()
                except OSError:
                    pass
        except Exception:
            pass

    def set_status(self, status: str) -> None:
        self.status = status

    def update_profile(self, display: str = "", dept: str = "",
                       role: str = "", name: str = "",
                       anydesk: str | None = None, rustdesk: str | None = None,
                       hw: dict[str, str] | None = None,
                       status_msg: str | None = None) -> None:
        """Atualiza dados anunciados no beacon (tela Informações do Usuário)."""
        with self._lock:
            if name:
                self.name = name
            if display:
                self.display = display
            if dept:
                self.dept = dept
            self.role = role
            if anydesk is not None:
                self.anydesk = anydesk
            if rustdesk is not None:
                self.rustdesk = rustdesk
            if hw is not None:
                self.hw = dict(hw)
            if status_msg is not None:
                self.status_msg = status_msg

    def get_peers(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._peers)

    def get_roster(self) -> dict[str, dict]:
        """Online + offline conhecidos (p/ 'Ocultar usuários offline' desmarcado)."""
        with self._lock:
            out = dict(self._known)
            for ip, p in self._peers.items():
                out[ip] = dict(p)
            return out

    def add_peer_manual(self, ip: str, name: str = "manual") -> None:
        """Para teste local (2 instâncias no mesmo PC) ou rede sem broadcast."""
        with self._lock:
            info = {"name": name, "display": name, "dept": "Geral",
                    "user": "?", "status": "online",
                    "ts": time.time(), "manual": True}
            self._peers[ip] = dict(info)
            self._known[ip] = dict(info)

    # -- faixas de rede (estilo Softros: tela Rede -> Transmissão) ------
    def get_ranges(self) -> list[str]:
        with self._lock:
            return list(self._ranges)

    def _persist(self) -> None:
        try:
            networks.save_ranges(self.networks_file, self._ranges)
        except OSError:
            pass

    def add_range(self, spec: str) -> int:
        """Cadastra '10.0.0.1-10.0.0.254'. Retorna nº de IPs. Levanta ValueError."""
        ips = networks.expand_range(spec)  # valida + limite
        with self._lock:
            if spec not in self._ranges:
                self._ranges.append(spec)
                self._targets = networks.expand_all(self._ranges)
        self._persist()
        return len(ips)

    def del_range(self, spec: str) -> bool:
        with self._lock:
            if spec in self._ranges:
                self._ranges.remove(spec)
                self._targets = networks.expand_all(self._ranges)
                removed = True
            else:
                removed = False
        if removed:
            self._persist()
        return removed

    # -- loops internos ----------------------------------------------
    def _targets_snapshot(self) -> list[str]:
        with self._lock:
            return list(self._targets)

    def _beacon_msg(self) -> bytes:
        with self._lock:
            name, user, status = self.name, self.user, self.status
            display, dept, role = self.display, self.dept, self.role
            anydesk, rustdesk = self.anydesk, self.rustdesk
            status_msg = self.status_msg
            app_version = self.app_version
            hw = dict(self.hw)
        return json.dumps(
            protocol.make_beacon(name, user, status, display, dept, role,
                                 anydesk, rustdesk,
                                 hw.get("cpu", ""), hw.get("ram", ""),
                                 hw.get("ram_type", ""), hw.get("disk", ""),
                                 hw.get("os", ""), status_msg, app_version)
        ).encode(config.ENCODING)

    def _send_ping(self) -> None:
        """Sonda imediata ao abrir: pares respondem com beacon (~1 RTT)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2.0)
            msg = json.dumps(protocol.make_ping(self.name, self.user)).encode(config.ENCODING)
            try:
                sock.sendto(msg, (self.broadcast, self.send_port))
            except OSError:
                pass
            for ip in self._targets_snapshot():
                try:
                    sock.sendto(msg, (ip, self.send_port))
                except OSError:
                    continue
        except OSError:
            pass
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def diag(self) -> dict:
        """Snapshot p/ diagnóstico (tela Rede). Thread-safe."""
        with self._lock:
            return {"udp_port": self.udp_port, "bind_ok": self.bind_ok,
                    "bind_error": self.bind_error, "targets": len(self._targets),
                    "ranges": list(self._ranges), "last_tx": self.last_tx,
                    "tx_count": self.tx_count, "tx_errors": self.tx_errors,
                    "last_rx": self.last_rx, "last_rx_from": self.last_rx_from,
                    "online": len(self._peers), "known": len(self._known)}

    def _beacon_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            round = 0
            while not self._stop.is_set():
                round += 1
                sent_ok, sent_err = 0, 0
                try:
                    msg = self._beacon_msg()
                    # 1. broadcast local (mesma sub-rede)
                    try:
                        sock.sendto(msg, (self.broadcast, self.send_port))
                        sent_ok += 1
                    except OSError:
                        sent_err += 1
                    # 2. unicast dirigido p/ cada IP das faixas (atravessa VPN).
                    #    Envio ritmado: rajadas curtas p/ não sofrer flood/drop.
                    n = 0
                    for ip in self._targets_snapshot():
                        try:
                            sock.sendto(msg, (ip, self.send_port))
                            sent_ok += 1
                        except OSError:
                            sent_err += 1
                            continue
                        n += 1
                        if n % config.BEACON_PACE_EVERY == 0:
                            time.sleep(config.BEACON_PACE_PAUSE)
                except OSError:
                    sent_err += 1
                with self._lock:
                    if sent_ok:
                        self.last_tx = time.time()
                    self.tx_count += sent_ok
                    self.tx_errors += sent_err
                # rajadas de boas-vindas rápidas ao abrir, depois intervalo normal
                pause = 1.0 if round < config.HELLO_ROUNDS else config.BEACON_INTERVAL
                self._stop.wait(pause)
        finally:
            sock.close()

    def _listen_loop(self) -> None:
        while not self._stop.is_set():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:  # SO_REUSEPORT permite 2 instâncias p/ teste no Linux/macOS
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except (AttributeError, OSError):
                    pass
                try:
                    sock.bind(("", self.udp_port))
                except OSError as e:
                    with self._lock:
                        self.bind_ok = False
                        self.bind_error = (f"porta UDP {self.udp_port} em uso: {e}. "
                                           "Feche a outra cópia/Softros e aguarde.")
                    sock.close()
                    self._stop.wait(5.0)
                    continue  # tenta de novo (porta pode liberar)
                with self._lock:
                    self.bind_ok = True
                    self.bind_error = ""
                sock.settimeout(1.0)
                while not self._stop.is_set():
                    try:
                        data, addr = sock.recvfrom(65535)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    self._on_datagram(data, addr[0], sock)
            finally:
                try:
                    sock.close()
                except OSError:
                    pass

    def _is_self(self, obj: dict, ip: str = "") -> bool:
        # Mesmo nome+usuário = meu próprio beacon (2ª cópia no mesmo PC).
        # (O ip é ignorado de propósito: 2 instâncias de teste no mesmo PC
        # falam via 127.0.0.1 com nomes diferentes e precisam se enxergar.)
        _ = ip
        return obj.get("name") == self.name and obj.get("user") == self.user

    def _on_datagram(self, data: bytes, ip: str, sock: socket.socket | None = None) -> None:
        try:
            obj = json.loads(data.decode(config.ENCODING))
        except (ValueError, UnicodeDecodeError):
            return
        kind = obj.get("type")
        if kind == "ping":
            # sonda de um par abrindo agora: responde na hora (unicast)
            if not self._is_self(obj, ip) and sock is not None:
                try:
                    sock.sendto(self._beacon_msg(), (ip, self.send_port))
                    with self._lock:
                        self.last_tx = time.time()
                        self.tx_count += 1
                except OSError:
                    pass
            return
        if kind != "beacon":
            return
        # ignora o próprio beacon (mesmo nome+usuário vindo do próprio IP)
        if self._is_self(obj, ip):
            return
        with self._lock:
            status = str(obj.get("status", "online"))
            info = self._build_info(obj, via="udp")
            if status == "offline":
                # saída graciosa: some dos online na hora, fica no histórico
                self._peers.pop(ip, None)
                self._known[ip] = dict(info)
            else:
                self._peers[ip] = dict(info)
                self._known[ip] = dict(info)
            self.last_rx = time.time()
            self.last_rx_from = ip

    def _reaper_loop(self) -> None:
        while not self._stop.is_set():
            now = time.time()
            with self._lock:
                dead = [ip for ip, p in self._peers.items()
                        if not p.get("manual") and now - p.get("ts", 0) > config.PEER_TIMEOUT]
                for ip in dead:
                    # marca offline no histórico em vez de sumir (tela Geral:
                    # "Ocultar usuários offline" decide se exibe)
                    info = dict(self._peers.pop(ip))
                    info["status"] = "offline"
                    self._known[ip] = info
            self._stop.wait(5.0)
