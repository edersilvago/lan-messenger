"""Histórico local em SQLite (cada máquina guarda o seu)."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, peer TEXT, direction TEXT,
  text TEXT, ts REAL
);
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY, peer TEXT, filename TEXT,
  size INTEGER, path TEXT, ts REAL
);
"""


class Store:
    def __init__(self, path: str | Path | None = None):
        from . import config as _config
        self.path = Path(path) if path else _config.APP_DATA / "lan_history.db"
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(SCHEMA)

    def add_message(self, msg_id: str, peer: str, direction: str, text: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?)",
            (msg_id, peer, direction, text, time.time()))
        self._conn.commit()

    def add_file(self, file_id: str, peer: str, filename: str, size: int, path: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)",
            (file_id, peer, filename, size, path, time.time()))
        self._conn.commit()

    def recent_messages(self, limit: int = 50) -> list[tuple]:
        cur = self._conn.execute(
            "SELECT peer, direction, text, datetime(ts,'unixepoch','localtime')"
            " FROM messages ORDER BY ts DESC LIMIT ?", (limit,))
        return list(cur.fetchall())

    def messages_with(self, peer: str, limit: int = 100) -> list[tuple[str, str, str]]:
        """Histórico com um peer (p/ janela de conversa). [(direction, text, ts)]."""
        cur = self._conn.execute(
            "SELECT direction, text, datetime(ts,'unixepoch','localtime')"
            " FROM messages WHERE peer=? ORDER BY ts ASC LIMIT ?", (peer, limit))
        return list(cur.fetchall())

    def list_peers(self) -> list[str]:
        """Peers com histórico (ordenados)."""
        cur = self._conn.execute("SELECT DISTINCT peer FROM messages ORDER BY peer")
        return [r[0] for r in cur.fetchall()]

    def search_messages(self, query: str, limit: int = 200) -> list[tuple[str, str, str, str]]:
        """Busca case-insensitive no histórico. [(peer, direction, text, ts)]."""
        cur = self._conn.execute(
            "SELECT peer, direction, text, datetime(ts,'unixepoch','localtime')"
            " FROM messages WHERE text LIKE ? ORDER BY ts DESC LIMIT ?",
            (f"%{query}%", limit))
        return list(cur.fetchall())
