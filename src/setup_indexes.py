# src/setup_indexes.py
import logging
import asyncio
import sys
import os
from typing import List, Optional

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sqlalchemy import make_url
from src.config import settings


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define paths
RULES_DIR = "dnd_src_material/rules_and_supplements"
CAMPAIGNS_DIR = "dnd_src_material/custom_campaigns"
VECTOR_TABLE_PREFIX = "dnd_bot_"

async def get_vector_store(table_name: str) -> PGVectorStore:
    """Creates and returns a PGVectorStore instance for a given table name."""
    url = make_url(settings.DATABASE_URL)
    return PGVectorStore.from_params(
        database=url.database,
        host=url.host,
        password=url.password,
        port=url.port,
        user=url.username,
        table_name=f"{VECTOR_TABLE_PREFIX}{table_name}",
        embed_dim=settings.vector_store_dim
    )

async def create_index(
    index_name: str, 
    embed_model, 
    directory: Optional[str] = None, 
    files: Optional[List[str]] = None
):
    """Creates a vector index from documents in a directory or a list of files."""
    if not directory and not files:
        logging.error("Either a directory or a list of files must be provided.")
        return
        
    source = directory if directory else files
    logging.info(f"Starting index creation for '{index_name}' from source '{source}'...")

    try:
        vector_store = await get_vector_store(index_name)

        logging.info(f"Loading documents from {source}...")
        reader = SimpleDirectoryReader(input_dir=directory, input_files=files)
        documents = reader.load_data()

        if not documents:
            logging.warning(f"No documents found in {source}. Skipping index creation for '{index_name}'.")
            return

        logging.info(f"Found {len(documents)} documents/parts. Creating storage context...")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        logging.info(f"Creating index '{index_name}'... This may take a while.")
        VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=embed_model,
            show_progress=True
        )
        logging.info(f"Successfully created index '{index_name}'.")

    except Exception as e:
        logging.error(f"Failed to create index '{index_name}': {e}")

async def main():
    """Main function to set up all necessary indexes."""
    logging.info("Initializing embedding model...")
    embed_model = HuggingFaceEmbedding(model_name=settings.embedding_model)

    # 1. Create the unified rules index from a directory
    await create_index("rules", embed_model, directory=RULES_DIR)

    # 2. Create a separate index for each campaign file
    if os.path.isdir(CAMPAIGNS_DIR):
        for campaign_file in os.listdir(CAMPAIGNS_DIR):
            campaign_path = os.path.join(CAMPAIGNS_DIR, campaign_file)
            if os.path.isfile(campaign_path):
                index_name = os.path.splitext(campaign_file)[0].lower().replace(" ", "_").replace("'", "")
                await create_index(f"campaign_{index_name}", embed_model, files=[campaign_path])

    logging.info("All indexes have been processed.")

if __name__ == "__main__":
    asyncio.run(main())
