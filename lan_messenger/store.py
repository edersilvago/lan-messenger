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
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY, peer TEXT, text TEXT, ts REAL
);
CREATE TABLE IF NOT EXISTS replies (
  msg_id TEXT PRIMARY KEY, reply_id TEXT, reply_name TEXT, reply_text TEXT
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

    def add_message_once(self, msg_id: str, peer: str,
                         direction: str, text: str) -> bool:
        """Grava somente ids novos. Retorna False em reentrega duplicada."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?)",
            (msg_id, peer, direction, text, time.time()))
        self._conn.commit()
        return cur.rowcount == 1

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
            " FROM (SELECT direction, text, ts, rowid AS rid"
            "       FROM messages WHERE peer=?"
            "       ORDER BY ts DESC, rowid DESC LIMIT ?)"
            " ORDER BY ts ASC, rid ASC", (peer, limit))
        return list(cur.fetchall())

    def messages_with_ids(self, peer: str,
                          limit: int = 100) -> list[tuple[str, str, str, str]]:
        """Como messages_with, mas com o id (marca balão pendente)."""
        cur = self._conn.execute(
            "SELECT id, direction, text, datetime(ts,'unixepoch','localtime')"
            " FROM (SELECT id, direction, text, ts, rowid AS rid"
            "       FROM messages WHERE peer=?"
            "       ORDER BY ts DESC, rowid DESC LIMIT ?)"
            " ORDER BY ts ASC, rid ASC", (peer, limit))
        return list(cur.fetchall())

    # -- fila de saída (v1.29): mensagens p/ quem estava offline ----------
    def queue_message(self, msg_id: str, peer: str, text: str) -> None:
        """Guarda a mensagem para reenvio automático quando o peer voltar."""
        self._conn.execute(
            "INSERT OR REPLACE INTO outbox VALUES (?,?,?,?)",
            (msg_id, peer, text, time.time()))
        self._conn.commit()

    def pending_messages(self) -> list[tuple[str, str, str]]:
        """Fila pendente, mais antiga primeiro. [(id, peer, text)]."""
        cur = self._conn.execute(
            "SELECT id, peer, text FROM outbox ORDER BY ts ASC")
        return list(cur.fetchall())

    def pending_ids(self, peer: str | None = None) -> set[str]:
        """Ids ainda não entregues (peer=None: todos)."""
        if peer is None:
            cur = self._conn.execute("SELECT id FROM outbox")
        else:
            cur = self._conn.execute("SELECT id FROM outbox WHERE peer=?", (peer,))
        return {r[0] for r in cur.fetchall()}

    def pending_count(self, peer: str | None = None) -> int:
        return len(self.pending_ids(peer))

    def drop_pending(self, msg_id: str) -> None:
        """Remove da fila (entregue ou descartada)."""
        self._conn.execute("DELETE FROM outbox WHERE id=?", (msg_id,))
        self._conn.commit()

    # -- respostas (v1.30): citação de mensagem específica ----------------
    def set_reply(self, msg_id: str, reply_id: str, name: str, text: str) -> None:
        """Liga a mensagem ao que ela responde (para exibir a citação)."""
        self._conn.execute(
            "INSERT OR REPLACE INTO replies VALUES (?,?,?,?)",
            (msg_id, reply_id, name, text))
        self._conn.commit()

    def get_reply(self, msg_id: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT reply_id, reply_name, reply_text FROM replies WHERE msg_id=?",
            (msg_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "text": row[2]}

    def replies_with(self, peer: str) -> dict[str, dict]:
        """Citações das mensagens trocadas com um peer. {msg_id: reply}."""
        cur = self._conn.execute(
            "SELECT r.msg_id, r.reply_id, r.reply_name, r.reply_text"
            " FROM replies r JOIN messages m ON m.id = r.msg_id"
            " WHERE m.peer=?", (peer,))
        return {r[0]: {"id": r[1], "name": r[2], "text": r[3]}
                for r in cur.fetchall()}

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
