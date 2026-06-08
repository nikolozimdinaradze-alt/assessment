import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect

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
