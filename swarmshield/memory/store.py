"""Shared memory for the swarm: a small SQLite table where every entry keeps who wrote it, which
sources it was derived from and whether those sources were trusted.

Write filters are the hook defences use (Step 5): each is called with the entry about to be
stored and returns the entry (possibly rewritten) or None to block the write.
"""

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass

WriteFilter = Callable[["Entry"], "Entry | None"]


@dataclass(frozen=True)
class Entry:
    id: int
    round: int
    author: str
    text: str
    provenance: tuple[str, ...] = ()
    trusted: bool = True


class SharedMemory:
    def __init__(self, path: str = ":memory:", write_filters: Sequence[WriteFilter] = ()):
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "round INTEGER, author TEXT, text TEXT, provenance TEXT, trusted INTEGER)"
        )
        self.write_filters = list(write_filters)

    def write(
        self,
        text: str,
        author: str,
        round: int,
        provenance: Sequence[str] = (),
        trusted: bool = True,
    ) -> Entry | None:
        """Store an entry and return it, or return None if a write filter blocked it."""
        entry: Entry | None = Entry(0, round, author, text, tuple(provenance), trusted)
        for check in self.write_filters:
            entry = check(entry) if entry else None
        if entry is None:
            return None
        cur = self.db.execute(
            "INSERT INTO memory (round, author, text, provenance, trusted) VALUES (?,?,?,?,?)",
            (entry.round, entry.author, entry.text, "|".join(entry.provenance), int(entry.trusted)),
        )
        self.db.commit()
        return Entry(
            cur.lastrowid, entry.round, entry.author, entry.text, entry.provenance, entry.trusted
        )

    def read(self, limit: int | None = None) -> list[Entry]:
        """Entries oldest first; with `limit`, only the most recent ones."""
        rows = self.db.execute(
            "SELECT id, round, author, text, provenance, trusted FROM memory ORDER BY id"
        ).fetchall()
        entries = [
            Entry(i, r, a, t, tuple(p.split("|")) if p else (), bool(tr))
            for i, r, a, t, p, tr in rows
        ]
        return entries[-limit:] if limit else entries
