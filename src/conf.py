import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class Settings(BaseSettings):
    DB_URI: str = "data/assessment.db"

    OPENAI_API_KEY: str
    KNOWLEDGE_BASE_DIR: str = "knowledge"

    CONVERSATION_HISTORY_LIMIT: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# noinspection PyArgumentList
settings = Settings()
