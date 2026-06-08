import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect

from src import __version__
from src.chatbot import QAChatbot
from src.conf import settings
from src.database import apply_migrations, get_db
from src.schemas import (
    ChatMessage,
    ChatSession,
    CreateChatSessionRequest,
    DeleteChatSessionResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    apply_migrations(settings.DB_URI)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health-check")
async def health_check():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {
        "version": __version__,
    }


@app.get("/chat-session", response_model=list[ChatSession])
async def list_chat_sessions(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        """
        SELECT
            id,
            summary,
            created_at
        FROM chat_sessions
        ORDER BY created_at DESC
        """
    )

    return [dict(row) for row in cursor.fetchall()]


@app.get("/chat-messages/{session_id}", response_model=list[ChatMessage])
async def retrieve_chat_messages(
    session_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    session = db.execute(
        """
        SELECT id
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    cursor = db.execute(
        """
        SELECT
            id,
            chat_session_id,
            role,
            content,
            created_at
        FROM chat_messages
        WHERE chat_session_id = ?
        ORDER BY created_at ASC
        """,
        (session_id,),
    )

    return [dict(row) for row in cursor.fetchall()]


@app.post("/chat-session", response_model=ChatSession, status_code=201)
async def create_chat_session(
    payload: CreateChatSessionRequest,
    db: sqlite3.Connection = Depends(get_db),
):
    cursor = db.execute(
        """
        INSERT INTO chat_sessions (summary)
        VALUES (?)
        """,
        (payload.summary,),
    )

    db.commit()

    session = db.execute(
        """
        SELECT
            id,
            summary,
            created_at
        FROM chat_sessions
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()

    return dict(session)


@app.delete("/chat-session/{session_id}", response_model=DeleteChatSessionResponse)
async def delete_chat_session(
    session_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    cursor = db.execute(
        """
        DELETE FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,),
    )

    db.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {"status": "deleted"}


@app.websocket("/chat/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
):
    await websocket.accept()

    db = sqlite3.connect(
        settings.DB_URI,
        check_same_thread=False,
    )
    db.row_factory = sqlite3.Row

    try:
        chatbot = QAChatbot(
            chat_session_id=session_id,
            db_connection=db,
        )

        if not chatbot.check_session_id():
            await websocket.send_json(
                {
                    "error": "Chat session not found",
                }
            )
            await websocket.close()
            return

        while True:
            message = await websocket.receive_text()

            completion = await chatbot.get_completion(
                message,
            )

            await websocket.send_json(
                {
                    "role": "assistant",
                    "content": completion,
                }
            )

    except WebSocketDisconnect:
        pass

    finally:
        db.close()
