"""Settings contract: every attribute callers read must exist on src.config.settings."""

from src.config import Settings, settings


REQUIRED_ATTRS = (
    "DATABASE_URL",
    "DM_BACKEND",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_THINKING_BUDGET",
    "GEMINI_MAX_OUTPUT_TOKENS",
    "GEMINI_TIMEOUT_SEC",
    "XAI_API_KEY",
    "LOCAL_MODEL_NAME",
    "LOCAL_MODEL_PATH",
    "LOCAL_LOAD_IN_4BIT",
    "LOCAL_QUANTIZATION",
    "MAX_MODEL_LEN",
    "INTENT_BACKEND",
    "INTENT_EMBED_MODEL",
    "INTENT_EMBED_K",
    "INTENT_MECHANICS_MARGIN",
    "INTENT_MODEL_NAME",
    "INTENT_DEVICE",
    "INTENT_TIMEOUT_SEC",
    "INTENT_MAX_NEW_TOKENS",
    "INTENT_RULES_FALLBACK",
    "DISCORD_TOKEN",
    "BOT_CHANNEL_ID",
    "OWNER_ID",
    "custom_campaign_path",
    "campaign_pdf_path",
    "srd_pdf_path",
    "index_storage_path",
    "embedding_model",
    "vector_store_dim",
    "similarity_top_k",
    "chunk_size",
    "chunk_overlap",
)


def test_settings_exposes_contract_fields():
    for name in REQUIRED_ATTRS:
        assert hasattr(settings, name), name


def test_defaults_match_dell_gemini_setup():
    fields = Settings.model_fields
    assert fields["DM_BACKEND"].default == "gemini"
    assert fields["GEMINI_MODEL"].default == "gemini-3.5-flash-lite"
    assert fields["GEMINI_THINKING_BUDGET"].default == 0
    assert fields["custom_campaign_path"].default == "dnd_src_material/custom_campaigns"
    assert fields["vector_store_dim"].default == 384


def test_placeholder_discord_ids_become_zero():
    assert Settings._placeholder_ids_to_zero("your_channel_id_here") == 0
    assert Settings._placeholder_ids_to_zero("12") == 12
