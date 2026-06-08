import pytest

from src.__version__ import __version__


@pytest.mark.asyncio
async def test_health_check_returns_ok(async_client):
    response = await async_client.get("/health-check")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


@pytest.mark.asyncio
async def test_version_returns_current_version(async_client):
    response = await async_client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": __version__,
    }


@pytest.mark.asyncio
async def test_list_chat_sessions_empty(async_client):
    response = await async_client.get("/chat-session")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_chat_sessions_returns_sessions(
    async_client,
    session_id,
):
    response = await async_client.get("/chat-session")

    assert response.status_code == 200

    sessions = response.json()

    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["summary"] == "Test session"


@pytest.mark.asyncio
async def test_create_chat_session(async_client):
    response = await async_client.post(
        "/chat-session",
        json={
            "summary": "Login tests",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] > 0
    assert body["summary"] == "Login tests"
    assert "created_at" in body


@pytest.mark.asyncio
async def test_retrieve_chat_messages_empty(
    async_client,
    session_id,
):
    response = await async_client.get(
        f"/chat-messages/{session_id}",
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_retrieve_chat_messages_not_found(
    async_client,
):
    response = await async_client.get(
        "/chat-messages/999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Chat session not found",
    }


@pytest.mark.asyncio
async def test_delete_chat_session(
    async_client,
    db_connection,
    session_id,
):
    response = await async_client.delete(
        f"/chat-session/{session_id}",
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "deleted",
    }

    session = db_connection.execute(
        """
        SELECT id
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()

    assert session is None


@pytest.mark.asyncio
async def test_delete_chat_session_not_found(
    async_client,
):
    response = await async_client.delete(
        "/chat-session/999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Chat session not found",
    }


@pytest.mark.asyncio
async def test_retrieve_chat_messages(
    async_client,
    session_with_messages,
):
    response = await async_client.get(
        f"/chat-messages/{session_with_messages}",
    )

    assert response.status_code == 200

    messages = response.json()

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
