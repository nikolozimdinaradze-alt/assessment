from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class CreateChatSessionRequest(BaseModel):
    summary: str | None = None


class ChatSession(BaseModel):
    id: int
    summary: str | None
    created_at: datetime


class ChatMessage(BaseModel):
    id: int
    chat_session_id: int
    role: MessageRole
    content: str
    created_at: datetime


class CreateChatSessionResponse(ChatSession):
    pass


class DeleteChatSessionResponse(BaseModel):
    status: str
