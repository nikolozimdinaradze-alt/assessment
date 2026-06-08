from time import sleep
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.chatbot import QAChatbot
from src.schemas import MessageRole


def test_check_session_id_returns_true(
    chatbot,
):
    assert chatbot.check_session_id() is True


def test_check_session_id_returns_false(
    db_connection,
):
    chatbot = QAChatbot(
        chat_session_id=999,
        db_connection=db_connection,
    )

    assert chatbot.check_session_id() is False


def test_save_conversation_history(
    chatbot,
    db_connection,
):
    chatbot._save_conversation_history(
        role=MessageRole.USER,
        content="Hello",
    )

    row = db_connection.execute(
        """
        SELECT role, content
        FROM chat_messages
        """
    ).fetchone()

    assert row["role"] == "user"
    assert row["content"] == "Hello"


def test_get_conversation_history(
    chatbot,
    db_connection,
):
    chatbot._save_conversation_history(
        MessageRole.USER,
        "Question",
    )
    sleep(1)
    chatbot._save_conversation_history(
        MessageRole.ASSISTANT,
        "Answer",
    )

    history = chatbot._get_conversation_history()

    assert history == [
        {
            "role": "user",
            "content": "Question",
        },
        {
            "role": "assistant",
            "content": "Answer",
        },
    ]


@patch(
    "src.chatbot.Path.glob",
)
def test_retrieve_file_titles(
    mock_glob,
):
    mock_glob.return_value = [
        Mock(name="main_page_tests.txt"),
        Mock(name="profile_page_tests.txt"),
    ]

    mock_glob.return_value[0].name = "main_page_tests.txt"
    mock_glob.return_value[1].name = "profile_page_tests.txt"

    result = QAChatbot._retrieve_file_titles()

    assert result == [
        "main_page_tests.txt",
        "profile_page_tests.txt",
    ]


@patch(
    "pathlib.Path.read_text",
)
def test_retrieve_file_context(
    mock_read_text,
):
    mock_read_text.return_value = "content"

    result = QAChatbot._retrieve_file_context(
        "test.txt",
    )

    assert result == "content"


@pytest.mark.asyncio
async def test_retrieve_related_knowledge_base_no_files(
    chatbot,
):
    with patch.object(
        chatbot,
        "_retrieve_file_titles",
        return_value=[],
    ):
        result = await chatbot._retrieve_related_knowledge_base(
            "login test",
        )

    assert result == ""


@pytest.mark.asyncio
async def test_retrieve_related_knowledge_base(
    chatbot,
):
    with (
        patch.object(
            chatbot,
            "_retrieve_file_titles",
            return_value=[
                "main_page.txt",
                "profile_page.txt",
            ],
        ),
        patch.object(
            chatbot,
            "_retrieve_file_context",
            side_effect=[
                "main content",
                "profile content",
            ],
        ),
    ):
        chatbot.openai_client.responses.create = AsyncMock(
            return_value=Mock(
                output_text='["main_page.txt"]',
            )
        )

        result = await chatbot._retrieve_related_knowledge_base(
            "login",
        )

    assert "main_page.txt" in result
    assert "main content" in result


@pytest.mark.asyncio
async def test_retrieve_related_knowledge_base_trims_files(
    chatbot,
):
    with (
        patch.object(
            chatbot,
            "_retrieve_file_titles",
            return_value=[
                "1.txt",
                "2.txt",
                "3.txt",
            ],
        ),
        patch.object(
            chatbot,
            "_retrieve_file_context",
            return_value="content",
        ),
    ):
        chatbot.openai_client.responses.create = AsyncMock(
            return_value=Mock(
                output_text='["1.txt","2.txt","3.txt"]',
            )
        )

        result = await chatbot._retrieve_related_knowledge_base(
            "login",
        )

    assert "1.txt" in result
    assert "2.txt" in result
    assert "3.txt" not in result


@pytest.mark.asyncio
async def test_retrieve_related_knowledge_base_invalid_json(
    chatbot,
):
    with patch.object(
        chatbot,
        "_retrieve_file_titles",
        return_value=["file.txt"],
    ):
        chatbot.openai_client.responses.create = AsyncMock(
            return_value=Mock(
                output_text="not json",
            )
        )

        result = await chatbot._retrieve_related_knowledge_base(
            "login",
        )

    assert result == ""


@pytest.mark.asyncio
async def test_get_completion(
    chatbot,
    db_connection,
):
    with (
        patch.object(
            chatbot,
            "_retrieve_related_knowledge_base",
            return_value="KB content",
        ),
    ):
        chatbot.openai_client.responses.create = AsyncMock(
            return_value=Mock(
                output_text="Generated answer",
            )
        )

        result = await chatbot.get_completion(
            "How do I login?",
        )

    assert result == "Generated answer"

    messages = db_connection.execute(
        """
        SELECT role, content
        FROM chat_messages
        ORDER BY id
        """
    ).fetchall()

    assert len(messages) == 2

    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "How do I login?"

    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Generated answer"
