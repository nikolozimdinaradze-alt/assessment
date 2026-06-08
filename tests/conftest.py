import sqlite3
from typing import Generator

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient

from src.chatbot import QAChatbot
from src.database import apply_migrations, get_db
from src.main import app


@pytest_asyncio.fixture
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    db_uri = ":memory:"
    conn = sqlite3.connect(db_uri)
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)

    yield conn

    conn.close()


@pytest_asyncio.fixture
async def async_client(db_connection):
    app.lifespan_context = None

    app.dependency_overrides[get_db] = lambda: db_connection

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def session_id(db_connection: sqlite3.Connection) -> int:
    cursor = db_connection.execute(
        """
        INSERT INTO chat_sessions (summary)
        VALUES (?)
        """,
        ("Test session",),
    )

    db_connection.commit()

    return cursor.lastrowid


@pytest.fixture
def session_with_messages(
    db_connection,
    session_id,
):
    db_connection.execute(
        """
        INSERT INTO chat_messages (
            chat_session_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            session_id,
            "user",
            "Hello",
        ),
    )

    db_connection.commit()

    return session_id


@pytest.fixture
def chatbot(
    db_connection,
    session_id,
):
    return QAChatbot(
        chat_session_id=session_id,
        db_connection=db_connection,
    )
