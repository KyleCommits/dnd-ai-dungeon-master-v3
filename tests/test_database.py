# tests/test_database.py
import asyncio
import logging
import sys
import os
import pytest
from sqlalchemy import text

# Add src to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import get_db_session, engine

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# --- Test Logic ---

@pytest.mark.asyncio
async def test_database_operations():
    """
    Tests basic database operations:
    1. Connect to the database.
    2. Create a test table.
    3. Insert data into the table.
    4. Query the data.
    5. Drop the test table.
    """
    logging.info("--- Database Operations Test ---")
    
    async with engine.begin() as conn:
        # 1. Create a test table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50)
            );
        """))
        logging.info("Test table created.")
        
        # 2. Insert data
        await conn.execute(text("INSERT INTO test_table (name) VALUES ('test_user');"))
        logging.info("Test data inserted.")
        
        # 3. Query the data
        result = await conn.execute(text("SELECT * FROM test_table;"))
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0].name == 'test_user'
        logging.info("Test data queried successfully.")
        
        # 4. Drop the test table
        await conn.execute(text("DROP TABLE test_table;"))
        logging.info("Test table dropped.")
        
    logging.info("--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_database_operations())
