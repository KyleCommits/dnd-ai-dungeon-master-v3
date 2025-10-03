# src/rag_manager.py
import logging
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.callbacks import CallbackManager
from sqlalchemy import make_url
from .config import settings
from .llm_manager import llm_manager
import asyncio
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VECTOR_TABLE_PREFIX = "data_"

class LocalLLMWrapper(CustomLLM):
    """Custom LLM wrapper for our local LLM manager."""
    
    context_window: int = 4096
    num_output: int = 256
    model_name: str = "local_llm"
    
    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )
    
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Synchronous completion - this shouldn't be called in our async setup."""
        # For safety, we'll run the async version synchronously
        import asyncio
        try:
            response = asyncio.run(self.acomplete(prompt, **kwargs))
            return response
        except Exception as e:
            logging.error(f"Error in sync complete: {e}")
            return CompletionResponse(text="Error: Could not generate response")
    
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Async completion using our local LLM manager."""
        try:
            if not llm_manager.pipeline:
                llm_manager.load_model()
            
            response_text = await llm_manager.generate(prompt, max_new_tokens=200)
            return CompletionResponse(text=response_text)
        except Exception as e:
            logging.error(f"Error in async complete: {e}")
            return CompletionResponse(text="Error: Could not generate response")
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """Streaming not implemented."""
        yield CompletionResponse(text="Streaming not supported")

class RAGManager:
    def __init__(self):
        self.embed_model = HuggingFaceEmbedding(model_name=settings.embedding_model)
        self.local_llm = LocalLLMWrapper()
        self.query_engines = {}
        self.db_url = make_url(settings.DATABASE_URL)

    async def get_query_engine(self, index_name: str):
        """
        Retrieves a query engine for a given index name.
        Initializes the engine if it's not already cached.
        """
        if index_name in self.query_engines:
            print(f"🔍 RAG: Using cached query engine for: {index_name}")
            return self.query_engines[index_name]

        # LlamaIndex PGVectorStore automatically adds data_ prefix, so use index_name directly
        table_name = index_name
        print(f"🔍 RAG: Initializing new query engine for index: {index_name}, table: {table_name}")
        try:
            # Handle different SQLAlchemy URL object attributes
            db_user = getattr(self.db_url, 'user', None) or getattr(self.db_url, 'username', None)
            db_password = getattr(self.db_url, 'password', None)
            db_host = getattr(self.db_url, 'host', None)
            db_port = getattr(self.db_url, 'port', None)
            db_name = getattr(self.db_url, 'database', None)
            
            logging.info(f"Database connection: {db_user}@{db_host}:{db_port}/{db_name}")
            
            vector_store = PGVectorStore.from_params(
                database=db_name,
                host=db_host,
                password=db_password,
                port=db_port,
                user=db_user,
                table_name=index_name,
                embed_dim=settings.vector_store_dim
            )
            
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embed_model
            )
            
            # Use retriever only (no LLM) since Gemini will process the context
            retriever = index.as_retriever(similarity_top_k=settings.similarity_top_k)
            query_engine = retriever
            self.query_engines[index_name] = query_engine
            logging.info(f"Query engine for '{index_name}' initialized successfully.")
            return query_engine

        except Exception as e:
            logging.error(f"Failed to initialize query engine for '{index_name}': {e}")
            return None

    async def query_rules(self, query_text: str) -> str:
        """Queries the rules index."""
        retriever = await self.get_query_engine("rules_vectors")
        if retriever:
            nodes = await retriever.aretrieve(query_text)
            if nodes:
                # Combine retrieved text chunks
                context_texts = [node.text for node in nodes]
                return "\n\n".join(context_texts)
            return "No relevant rules found."
        return "Error: Rules index not available."

    async def query_campaign(self, campaign_name: str, query_text: str) -> str:
        """Queries a specific campaign index."""
        print(f"🔍 RAG: query_campaign called with campaign='{campaign_name}', query='{query_text}'")
        index_name = f"campaign_{campaign_name.lower().replace(' ', '_')}"
        # LlamaIndex PGVectorStore automatically adds data_ prefix, so use index_name directly
        table_name = index_name
        print(f"🔍 RAG: Looking for campaign table: {table_name}")
        try:
            retriever = await self.get_query_engine(index_name)
        except Exception as e:
            print(f"❌ RAG: Exception in get_query_engine: {e}")
            return f"Error: Exception getting query engine: {e}"
        if retriever:
            print(f"🔍 RAG: Executing retrieval for query: '{query_text}'")
            print(f"🔍 RAG: Retriever type: {type(retriever)}")
            print(f"🔍 RAG: Similarity top_k setting: {settings.similarity_top_k}")
            try:
                # First, let's check what embedding model we're using for queries
                print(f"🔍 RAG: Query embedding model: {self.embed_model}")

                # Generate embedding for the query to see if it works
                query_embedding = self.embed_model.get_text_embedding(query_text)
                print(f"🔍 RAG: Query embedding generated, dimension: {len(query_embedding)}")
                print(f"🔍 RAG: Query embedding preview: {query_embedding[:5]}...")

                nodes = await retriever.aretrieve(query_text)
                print(f"🔍 RAG: Retrieved {len(nodes) if nodes else 0} nodes")

                if nodes:
                    for i, node in enumerate(nodes):
                        score = getattr(node, 'score', 'N/A')
                        print(f"🔍 RAG: Node {i} score: {score}, text preview: {node.text[:100]}...")
                    # Combine retrieved text chunks
                    context_texts = [node.text for node in nodes]
                    return "\n\n".join(context_texts)
                else:
                    print(f"🔍 RAG: No nodes returned - debugging similarity search...")

                    # Manual similarity test - let's try a direct SQL query
                    try:
                        import psycopg2
                        conn = psycopg2.connect(
                            host=self.db_url.host,
                            port=self.db_url.port,
                            user=getattr(self.db_url, 'username', None) or getattr(self.db_url, 'user', None),
                            password=self.db_url.password,
                            database=self.db_url.database
                        )
                        cursor = conn.cursor()

                        table_name = f"{VECTOR_TABLE_PREFIX}{index_name}"

                        # Check if table has data
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        print(f"🔍 RAG: Table {table_name} has {count} rows")

                        # Check if embeddings exist
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
                        embed_count = cursor.fetchone()[0]
                        print(f"🔍 RAG: {embed_count} rows have non-null embeddings")

                        # Try manual similarity search with relaxed threshold
                        query_vector = str(query_embedding).replace('[', '{').replace(']', '}')
                        cursor.execute(f"""
                            SELECT text, embedding <-> %s as distance
                            FROM {table_name}
                            WHERE embedding IS NOT NULL
                            ORDER BY distance
                            LIMIT 3
                        """, (query_vector,))

                        results = cursor.fetchall()
                        print(f"🔍 RAG: Manual similarity search returned {len(results)} results")
                        for i, (text, distance) in enumerate(results):
                            print(f"🔍 RAG: Manual result {i}: distance={distance}, text={text[:100]}...")

                        cursor.close()
                        conn.close()

                    except Exception as manual_e:
                        print(f"❌ RAG: Manual similarity test failed: {manual_e}")

                return "No relevant content found in campaign."
            except Exception as e:
                print(f"❌ RAG: Exception during retrieval: {e}")
                import traceback
                print(f"❌ RAG: Full traceback: {traceback.format_exc()}")
                return f"Error during retrieval: {e}"
        return f"Error: Campaign index for '{campaign_name}' not available."

    async def query_context(self, query_text: str, max_results: int = 3) -> str:
        """General context query that searches available campaign and rule indexes."""
        try:
            # Try rules first
            rules_response = await self.query_rules(query_text)
            
            # Try to find any available campaign indexes for additional context
            additional_context = ""
            
            # For now, return rules context (could be enhanced to search multiple indexes)
            if rules_response and rules_response != "Error: Rules query engine not available.":
                return rules_response[:500]  # Limit context size
            
            return ""
            
        except Exception as e:
            logging.error(f"Error querying context: {e}")
            return ""

# Global instance
rag_manager = RAGManager()

async def main():
    # Example usage for direct testing
    # Make sure the indexes have been created by running start_system.py once.
    logging.info("Testing RAGManager...")
    
    # Test rule query
    rules_query = "How does grappling work in 5e?"
    logging.info(f"Querying rules: '{rules_query}'")
    rules_response = await rag_manager.query_rules(rules_query)
    logging.info(f"Rules response: {rules_response}")

    # Test campaign query (assuming 'curse_of_strahd' index exists)
    campaign_query = "What is the village of Barovia like?"
    campaign_name = "Curse of Strahd"
    logging.info(f"Querying campaign '{campaign_name}': '{campaign_query}'")
    campaign_response = await rag_manager.query_campaign(campaign_name, campaign_query)
    logging.info(f"Campaign response: {campaign_response}")

if __name__ == "__main__":
    asyncio.run(main())
