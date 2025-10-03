# tests/test_new_campaign_prerequisites.py
import pytest
import os
import sys
import asyncio
from sqlalchemy import text

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the function to be tested with an alias to avoid name collision
from src.database import test_connection as test_db_connection
from src.database import get_all_campaign_structures, get_db_session
from src.config import settings
from src.llm_manager import llm_manager
from src.rag_setup import create_vector_store

# This fixture is often necessary for pytest-asyncio on Windows.
# It sets the default event loop policy before any tests run.
@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    # For other OS, the default policy is usually fine.
    return asyncio.get_event_loop_policy()

# This fixture applies the policy. It's autouse, so it runs for the session.
@pytest.fixture(scope="session", autouse=True)
def setup_event_loop_policy_fixture(event_loop_policy):
    asyncio.set_event_loop_policy(event_loop_policy)

# --- Prerequisite Tests ---

def test_source_materials_exist():
    """1. Checks if campaign source material exists."""
    campaign_dir = settings.campaign_pdf_path
    assert os.path.isdir(campaign_dir), f"Campaign directory not found at: {campaign_dir}"
    files = os.listdir(campaign_dir)
    assert len(files) > 0, f"No campaign source files found in {campaign_dir}."
    print(f"\n✅ Prerequisite 1/5: Found {len(files)} source campaign files.")

def test_prompt_template_exists():
    """2. Checks if the campaign generation prompt template exists."""
    prompt_path = "prompts/campaign_generation_prompt.txt"
    assert os.path.isfile(prompt_path), f"Campaign generation prompt not found at: {prompt_path}"
    print("✅ Prerequisite 2/5: Campaign generation prompt found.")

@pytest.mark.asyncio
async def test_database_connection():
    """3. Checks if the connection to the PostgreSQL database is successful."""
    is_connected = await test_db_connection()
    assert is_connected, "Failed to connect to the PostgreSQL database."
    print("✅ Prerequisite 3/5: Database connection successful.")

def test_llm_initialization_and_generation():
    """4. Checks if the LLM can be loaded and generate a response."""
    try:
        llm_manager.load_model()
        assert llm_manager.pipeline is not None, "LLM pipeline failed to initialize."
        response = llm_manager.generate("Hello, world!", max_new_tokens=5)
        assert response, "LLM generated an empty response."
        print("✅ Prerequisite 4/5: LLM loaded and generated a test response successfully.")
    except Exception as e:
        pytest.fail(f"An error occurred during LLM initialization or generation: {e}")

@pytest.mark.asyncio
async def test_campaign_analysis_data_exists():
    """5. Checks if the campaign_structures table has been populated."""
    structures = await get_all_campaign_structures()
    assert structures is not None, "Failed to query for campaign structures."
    assert len(structures) > 0, "The 'campaign_structures' table is empty."
    print(f"✅ Prerequisite 5/5: Found {len(structures)} campaign structures in the database.")

@pytest.mark.asyncio
async def test_pgvector_functionality():
    """Bonus Check: Verifies pgvector functionality."""
    test_table_name = "test_vector_table_delete_me"
    try:
        vector_store = await create_vector_store(table_name=test_table_name)
        assert vector_store is not None, "Failed to create a temporary vector store."
        
        # Clean up the test table.
        async for session in get_db_session():
            async with session.begin():
                # Use text() for executing raw SQL with SQLAlchemy 2.0 style
                await session.execute(text(f'DROP TABLE IF EXISTS "{test_table_name}";'))
            # No need for explicit commit with "async with session.begin()"
        print("✅ Bonus Check: pgvector functionality confirmed.")
    except Exception as e:
        pytest.fail(f"Failed to verify pgvector functionality. Error: {e}")




