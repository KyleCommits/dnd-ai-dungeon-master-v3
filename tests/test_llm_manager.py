# tests/test_llm_manager.py
import logging
import sys
import os

# Add src to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_manager import LLMManager

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# --- Test Logic ---

def run_test():
    """
    Loads the model via LLMManager and runs a test generation.
    """
    logging.info("--- LLM Manager Integration Test ---")
    
    try:
        # 1. Initialize and load the model
        # Note: This requires a GPU and can take a minute.
        manager = LLMManager()
        manager.load_model()
        
        # 2. Run a test generation
        prompt = "Describe a tense moment in a D&D game."
        logging.info(f"Sending test prompt: '{prompt}'")
        
        response = manager.generate(prompt, max_new_tokens=50)
        
        if response and "Error" not in response:
            logging.info(f"Successfully received completion: '{response}'")
            logging.info("Test passed!")
        else:
            logging.error(f"Test failed. Received an invalid response: {response}")

    except Exception as e:
        logging.error(f"Test failed with an exception: {e}", exc_info=True)
    
    logging.info("--- Test Complete ---")

if __name__ == "__main__":
    run_test()
