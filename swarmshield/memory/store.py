"""Shared memory for the swarm: a small SQLite table where every entry keeps who wrote it, which
sources it was derived from and whether those sources were trusted.

Write filters are the hook defences use (Step 5): each is called with the entry about to be
stored and returns the entry (possibly rewritten) or None to block the write.
"""

import re
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

    def last_id(self) -> int:
        return self.db.execute("SELECT COALESCE(MAX(id), 0) FROM memory").fetchone()[0]

    def search(self, query: str, limit: int) -> list["Entry"]:
        """The `limit` entries most relevant to `query` (shared words of 4+ letters), ties broken
        by recency, returned oldest first. This is how an agent retrieves memory, so an entry
        crafted to match the task keeps being retrieved however old it is."""
        words = set(re.findall(r"[a-z0-9]{4,}", query.lower()))

        def score(e: "Entry") -> int:
            return len(words & set(re.findall(r"[a-z0-9]{4,}", e.text.lower())))

        latest = {e.text: e for e in self.read()}  # repeated identical notes count once
        ranked = sorted(latest.values(), key=lambda e: (score(e), e.id), reverse=True)
        return sorted(ranked[:limit], key=lambda e: e.id)

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
