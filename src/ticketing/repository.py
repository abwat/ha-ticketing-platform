from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import Priority, Ticket, TicketComment, TicketStatus


class TicketRepository:
    def __init__(self, db_path: str | Path = "ticketing.sqlite") -> None:
        self.db_path = str(db_path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    assignee TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    due_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tickets_status_priority
                ON tickets(status, priority)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_comments_ticket_id
                ON comments(ticket_id, created_at)
                """
            )

    def save(self, ticket: Ticket) -> Ticket:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tickets
                    (id, title, description, priority, status, requester, assignee, created_at, updated_at, due_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    priority=excluded.priority,
                    status=excluded.status,
                    requester=excluded.requester,
                    assignee=excluded.assignee,
                    updated_at=excluded.updated_at,
                    due_at=excluded.due_at
                """,
                self._to_row(ticket),
            )
        return ticket

    def get(self, ticket_id: str) -> Ticket | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._from_row(row) if row else None

    def list(self, status: TicketStatus | None = None) -> list[Ticket]:
        sql = "SELECT * FROM tickets"
        params: tuple[str, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status.value,)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._from_row(row) for row in rows]

    def add_comment(self, comment: TicketComment) -> TicketComment:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO comments (id, ticket_id, author, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    comment.id,
                    comment.ticket_id,
                    comment.author,
                    comment.body,
                    comment.created_at.isoformat(),
                ),
            )
        return comment

    def list_comments(self, ticket_id: str) -> list[TicketComment]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE ticket_id = ? ORDER BY created_at ASC",
                (ticket_id,),
            ).fetchall()
        return [
            TicketComment(
                id=row["id"],
                ticket_id=row["ticket_id"],
                author=row["author"],
                body=row["body"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def _to_row(ticket: Ticket) -> tuple[str, ...]:
        return (
            ticket.id,
            ticket.title,
            ticket.description,
            ticket.priority.value,
            ticket.status.value,
            ticket.requester,
            ticket.assignee or "",
            ticket.created_at.isoformat(),
            ticket.updated_at.isoformat(),
            ticket.due_at.isoformat(),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Ticket:
        return Ticket(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=Priority(row["priority"]),
            status=TicketStatus(row["status"]),
            requester=row["requester"],
            assignee=row["assignee"] or None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            due_at=datetime.fromisoformat(row["due_at"]),
        )


class PostgresTicketRepository(TicketRepository):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        last_error: Exception | None = None
        for _ in range(20):
            try:
                self._init()
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error:
            raise last_error

    def _connect(self) -> Any:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tickets (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        status TEXT NOT NULL,
                        requester TEXT NOT NULL,
                        assignee TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        due_at TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_tickets_status_priority
                    ON tickets(status, priority)
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS comments (
                        id TEXT PRIMARY KEY,
                        ticket_id TEXT NOT NULL REFERENCES tickets(id),
                        author TEXT NOT NULL,
                        body TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_comments_ticket_id
                    ON comments(ticket_id, created_at)
                    """
                )
            conn.commit()

    def save(self, ticket: Ticket) -> Ticket:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tickets
                        (id, title, description, priority, status, requester, assignee, created_at, updated_at, due_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        description=excluded.description,
                        priority=excluded.priority,
                        status=excluded.status,
                        requester=excluded.requester,
                        assignee=excluded.assignee,
                        updated_at=excluded.updated_at,
                        due_at=excluded.due_at
                    """,
                    self._to_row(ticket),
                )
            conn.commit()
        return ticket

    def get(self, ticket_id: str) -> Ticket | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
                row = cur.fetchone()
        return self._from_mapping(row) if row else None

    def list(self, status: TicketStatus | None = None) -> list[Ticket]:
        sql = "SELECT * FROM tickets"
        params: tuple[str, ...] = ()
        if status:
            sql += " WHERE status = %s"
            params = (status.value,)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [self._from_mapping(row) for row in rows]

    def add_comment(self, comment: TicketComment) -> TicketComment:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO comments (id, ticket_id, author, body, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        comment.id,
                        comment.ticket_id,
                        comment.author,
                        comment.body,
                        comment.created_at.isoformat(),
                    ),
                )
            conn.commit()
        return comment

    def list_comments(self, ticket_id: str) -> list[TicketComment]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM comments WHERE ticket_id = %s ORDER BY created_at ASC",
                    (ticket_id,),
                )
                rows = cur.fetchall()
        return [
            TicketComment(
                id=row["id"],
                ticket_id=row["ticket_id"],
                author=row["author"],
                body=row["body"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def _from_mapping(row: dict[str, Any]) -> Ticket:
        return Ticket(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=Priority(row["priority"]),
            status=TicketStatus(row["status"]),
            requester=row["requester"],
            assignee=row["assignee"] or None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            due_at=datetime.fromisoformat(row["due_at"]),
        )


def build_repository(database_url: str | None, sqlite_path: str | Path) -> TicketRepository:
    if database_url and urlparse(database_url).scheme in {"postgres", "postgresql"}:
        return PostgresTicketRepository(database_url)
    return TicketRepository(sqlite_path)
