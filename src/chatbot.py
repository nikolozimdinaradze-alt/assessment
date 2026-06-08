import json
import logging
import sqlite3
from pathlib import Path

from openai import AsyncOpenAI

from src.conf import settings
from src.schemas import MessageRole


logger = logging.getLogger(__name__)


class QAChatbot:
    def __init__(
        self,
        chat_session_id: int,
        db_connection: sqlite3.Connection,
    ):
        self.chat_session_id = chat_session_id
        self.db_connection = db_connection

        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

    def check_session_id(self) -> bool:
        logger.info(f"Checking session id: {self.chat_session_id}")
        session = self.db_connection.execute(
            """
            SELECT id
            FROM chat_sessions
            WHERE id = ?
            """,
            (self.chat_session_id,),
        ).fetchone()
        session_exists = session is not None
        logger.info(f"Session exists: {session_exists}")
        return session_exists

    async def get_completion(
        self,
        message: str,
    ) -> str:
        logger.info(f"Saving conversation history of user, message: {message}, session: {self.chat_session_id}")
        self._save_conversation_history(
            role=MessageRole.USER,
            content=message,
        )
        logger.info(f"Retrieving knowledge base of user, message: {message}")
        knowledge_base = await self._retrieve_related_knowledge_base(
            message,
        )
        logger.info(f"Retrieving conversation history session {self.chat_session_id}.")
        conversation_history = self._get_conversation_history()
        logger.info(
            f"Retrieved total of {len(conversation_history)} conversation history. Session: {self.chat_session_id}"
        )

        logger.info(f"Constructing prompt ... Session: {self.chat_session_id}")
        messages = [
            {
                "role": "system",
                "content": """
        You are a QA testing assistant.

        When knowledge base information is provided:
        - Use ONLY the knowledge base to answer.
        - Do NOT invent additional information.
        - Do NOT use external knowledge.
        - If the answer cannot be found in the knowledge base, say:
          'I could not find this information in the knowledge base.'

        Keep answers concise and structured.
        """,
            }
        ]

        if knowledge_base:
            logger.info(f"Retrieved knowledge base for {self.chat_session_id} session: {knowledge_base[30:]}...")
            messages.append(
                {
                    "role": "system",
                    "content": f"Knowledge Base:\n\n{knowledge_base}",
                }
            )

        messages.extend(conversation_history)

        logger.info("Waiting for openai response ...")
        response = await self.openai_client.responses.create(
            model="gpt-5-mini",
            input=messages, # noqa
        )
        logger.info(f"Openai response received for session {self.chat_session_id}.")

        completion = response.output_text

        logger.info(f"Saving conversation history of assistant, session: {self.chat_session_id}")
        self._save_conversation_history(
            role=MessageRole.ASSISTANT,
            content=completion,
        )

        return completion

    def _save_conversation_history(
        self,
        role: MessageRole,
        content: str,
    ) -> None:
        self.db_connection.execute(
            """
            INSERT INTO chat_messages (
                chat_session_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                self.chat_session_id,
                role.value,
                content,
            ),
        )

        self.db_connection.commit()

    def _get_conversation_history(
        self,
    ) -> list[dict[str, str]]:
        cursor = self.db_connection.execute(
            """
            SELECT role,
                   content
            FROM chat_messages
            WHERE chat_session_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (
                self.chat_session_id,
                settings.CONVERSATION_HISTORY_LIMIT,
            ),
        )

        rows = cursor.fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in reversed(rows)
        ]

    async def _retrieve_related_knowledge_base(
        self,
        message: str,
    ) -> str:
        available_files = self._retrieve_file_titles()

        if not available_files:
            return ""

        response = await self.openai_client.responses.create(
            model="gpt-5-mini",
            input=[  # noqa
                {
                    "role": "system",
                    "content": f"""
                You are a knowledge-base file selector.
            
                Given a user query and available knowledge-base files,
                select up to {settings.KNOWLEDGE_BASE_FILES_LIMIT} files
                that are most likely to contain the answer.
            
                Return ONLY a JSON array of file names.
            
                Example:
                ["profile_page_tests.txt", "main_page_tests.txt"]
            
                If no files are relevant return:
                []
                """,
                },
                {
                    "role": "user",
                    "content": f"""
                User query:
                {message}
            
                Available files:
                {chr(10).join(available_files)}
                """,
                },
            ],
        )

        try:
            selected_files = json.loads(response.output_text)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse file selection response: %s",
                response.output_text,
            )
            return ""

        selected_files = [filename for filename in selected_files if filename in available_files]
        if len(selected_files) > settings.KNOWLEDGE_BASE_FILES_LIMIT:
            logger.warning(
                f"knowledge-base file selector retrieved more than limit of file number, retrieved {len(selected_files)} files."
            )
            logger.info(f"Reducing file number to keep in limit of {settings.KNOWLEDGE_BASE_FILES_LIMIT}.")
            selected_files = selected_files[: settings.KNOWLEDGE_BASE_FILES_LIMIT]
        logger.info(
            "Selected knowledge-base files: %s",
            selected_files,
        )

        contexts = []

        for filename in selected_files:
            content = self._retrieve_file_context(filename)
            contexts.append(f"=== {filename} ===\n{content}")

        return "\n\n".join(contexts)

    @staticmethod
    def _retrieve_file_titles() -> list[str]:
        knowledge_dir = Path(
            settings.KNOWLEDGE_BASE_DIR,
        )
        titles = [file.name for file in knowledge_dir.glob("*.txt")]
        logger.info(f"Total knowledge files {titles}.")
        return titles

    @staticmethod
    def _retrieve_file_context(
        filename: str,
    ) -> str:
        path = Path(settings.KNOWLEDGE_BASE_DIR) / filename
        logger.info(f"Retrieving file {filename} from {path}.")
        return path.read_text(
            encoding="utf-8",
        )
