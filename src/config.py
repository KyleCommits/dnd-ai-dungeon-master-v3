# src/config.py
"""App settings loaded from `.env`. Secrets belong in `.env` (gitignored), not here.

Field names are a contract: modules read them as `settings.<NAME>`, so renaming a
field breaks callers. Env lookup is case-insensitive.
"""
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dnd:dnd_local@localhost:5432/dnd_bot_v3"

    # DM narrator backend: "gemini" (cloud) or "local" (Transformers on CUDA)
    DM_BACKEND: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_THINKING_BUDGET: int = 0
    GEMINI_MAX_OUTPUT_TOKENS: int = 400
    GEMINI_TIMEOUT_SEC: float = 30.0
    XAI_API_KEY: Optional[str] = None

    # Local narrator (DM_BACKEND=local)
    LOCAL_MODEL_NAME: str = "mistralai/Mistral-7B-Instruct-v0.3"
    LOCAL_MODEL_PATH: Optional[str] = None
    LOCAL_LOAD_IN_4BIT: bool = True
    LOCAL_QUANTIZATION: str = "4bit"
    MAX_MODEL_LEN: int = 4096

    # Intent (src/intent_config.py reads os.environ first, then these)
    INTENT_BACKEND: str = "embed"
    INTENT_EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    INTENT_EMBED_K: int = 5
    INTENT_MECHANICS_MARGIN: float = 0.02
    INTENT_MODEL_NAME: str = "Qwen/Qwen2.5-1.5B-Instruct"
    INTENT_DEVICE: str = "cpu"
    INTENT_TIMEOUT_SEC: float = 20.0
    INTENT_MAX_NEW_TOKENS: int = 100
    INTENT_RULES_FALLBACK: bool = False

    # Legacy Discord bot (unused by the web app; dummy values are fine)
    DISCORD_TOKEN: Optional[str] = None
    BOT_CHANNEL_ID: int = 0
    OWNER_ID: int = 0

    # Paths and RAG
    custom_campaign_path: str = "dnd_src_material/custom_campaigns"
    campaign_pdf_path: str = "dnd_src_material/campaigns"
    srd_pdf_path: str = "dnd_src_material/rules_and_supplements/SRD-OGL_V5.1.pdf"
    index_storage_path: str = "./indexes"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_dim: int = 384
    similarity_top_k: int = 5
    chunk_size: int = 1024
    chunk_overlap: int = 200

    @field_validator("BOT_CHANNEL_ID", "OWNER_ID", mode="before")
    @classmethod
    def _placeholder_ids_to_zero(cls, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


settings = Settings()
