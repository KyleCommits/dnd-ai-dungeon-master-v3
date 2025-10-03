# src/rag_setup.py
import os
import asyncio
import uuid
import json
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy.engine.url import make_url
import asyncpg
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import settings

# --- Configuration ---
RULES_DIR = "dnd_src_material/rules_and_supplements"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RULES_VECTOR_TABLE = "rules_vectors"
RULES_DATA_TABLE = "data_rules_vectors"
EMBED_DIM = 384

# --- Reusable Functions for Campaign Generation ---
# These functions are called by the campaign orchestrator to create new campaign indexes.

async def create_vector_store(table_name: str, embed_dim: int = 384) -> PGVectorStore:
    """Creates and returns a PGVectorStore instance for a specific table."""
    db_url = make_url(settings.DATABASE_URL)
    return PGVectorStore.from_params(
        database=db_url.database,
        host=db_url.host,
        password=db_url.password,
        port=db_url.port,
        user=db_url.username,
        table_name=table_name,
        embed_dim=embed_dim
    )

async def create_index(vector_store: PGVectorStore, file_path: str) -> VectorStoreIndex:
    """
    Creates a VectorStoreIndex from a single campaign file.
    """
    print(f"Creating index from document: {file_path}")
    
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
    if not documents:
        raise ValueError(f"No documents could be loaded from file: {file_path}")
        
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # We can use the high-level API here as it's for campaign-specific, smaller indexes
    # and seems less prone to the silent failure.
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
    )
    print(f"Successfully created index from '{file_path}' into table '{vector_store.table_name}'.")
    return index

# --- Main Script for Initial Rules Setup ---
# This is intended to be run once to populate the main D&D rules database.

async def main():
    """
    A manual, direct-to-DB script to build the RAG index for D&D rules,
    bypassing LlamaIndex's failing high-level functions for this large task.
    """
    print("--- Starting RAG Indexing with Manual Database Script for D&D Rules---")

    # 1. Establish Database Connection
    conn = None
    try:
        print(f"Connecting to database...")
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        print("Database connection successful.")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to the database: {e}")
        return

    # 2. Create Tables Manually
    try:
        print(f"Ensuring tables '{RULES_VECTOR_TABLE}' and '{RULES_DATA_TABLE}' are created...")
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {RULES_VECTOR_TABLE} (
                id UUID PRIMARY KEY,
                embedding VECTOR({EMBED_DIM}),
                metadata_ JSONB
            );
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {RULES_DATA_TABLE} (
                id UUID PRIMARY KEY,
                text TEXT,
                metadata_ JSONB
            );
        """)
        print("Tables created or already exist.")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not create database tables: {e}")
        await conn.close()
        return

    # 3. Load Documents
    if not os.path.isdir(RULES_DIR):
        print(f"ERROR: Rules directory not found at: {RULES_DIR}. Aborting.")
        await conn.close()
        return
    
    rules_files = [os.path.join(RULES_DIR, f) for f in os.listdir(RULES_DIR) if os.path.isfile(os.path.join(RULES_DIR, f))]
    if not rules_files:
        print(f"WARNING: No files found in rules directory: {RULES_DIR}. Aborting.")
        await conn.close()
        return

    print(f"Loading {len(rules_files)} documents from '{RULES_DIR}'...")
    documents = SimpleDirectoryReader(input_files=rules_files).load_data()
    print(f"Loaded {len(documents)} initial document sections.")

    # 4. Process Documents into Nodes (Chunks)
    node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
    nodes = node_parser.get_nodes_from_documents(documents)
    print(f"Processed documents into {len(nodes)} text nodes (chunks).")

    # 5. Initialize Embedding Model
    print(f"Initializing embedding model: '{EMBEDDING_MODEL}'...")
    embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
    print("Embedding model loaded.")

    # 6. Generate Embeddings and Insert into Database
    print(f"Generating embeddings and inserting into database... This will take a moment.")
    total_nodes = len(nodes)
    success_count = 0
    for i, node in enumerate(nodes):
        print(f"  Processing node {i+1}/{total_nodes}...", end='\r')
        
        node_id = uuid.uuid4()
        text_to_embed = node.get_content()
        embedding = embed_model.get_text_embedding(text_to_embed)
        
        metadata = node.metadata.copy()
        metadata["_node_content"] = json.dumps(node.to_dict())
        metadata["_node_type"] = "TextNode"
        
        try:
            embedding_str = str(embedding)
            await conn.execute(
                f"INSERT INTO {RULES_DATA_TABLE} (id, text, metadata_) VALUES ($1, $2, $3)",
                node_id, text_to_embed, json.dumps(metadata)
            )
            await conn.execute(
                f"INSERT INTO {RULES_VECTOR_TABLE} (id, embedding, metadata_) VALUES ($1, $2, $3)",
                node_id, embedding_str, json.dumps(metadata)
            )
            success_count += 1
        except Exception as e:
            print(f"\nERROR: Failed to insert node {i+1}. Reason: {e}")
            continue
            
    print() 
    print(f"--- Indexing Complete ---")
    print(f"Successfully inserted {success_count}/{total_nodes} nodes into the database.")

    # 7. Close Connection
    await conn.close()
    print("Database connection closed.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
