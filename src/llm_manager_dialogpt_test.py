# src/llm_manager_dialogpt_test.py
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class LLMManagerDialoGPT:
    def __init__(self):
        self.pipeline = None
        self.model = None
        self.tokenizer = None
        self.model_name = "ckandemir/DialoGPT-small-crd3"  # CRD3-trained DialoGPT
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.xai_client = None  # Disabled for testing
        logging.info(f"DialoGPT LLMManager initialized to use device: {self.device}")

    def load_model(self):
        """Loads the DialoGPT model fine-tuned on CRD3 data."""
        if self.model:
            logging.info("DialoGPT model is already loaded.")
            return

        try:
            logging.info(f"Loading DialoGPT model: {self.model_name}...")

            # Load DialoGPT tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )

            # DialoGPT needs special tokens
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logging.info("DialoGPT model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load the DialoGPT model: {e}")
            self.model = None
            self.tokenizer = None

    async def generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        """
        Generates a response using DialoGPT with conversational context.
        """
        if not self.model or not self.tokenizer:
            logging.error("DialoGPT model is not initialized. Cannot generate text.")
            return "Error: DialoGPT model pipeline not initialized."

        try:
            import asyncio

            def _generate_sync():
                # Try a simple conversational format that DialoGPT might understand
                enhanced_prompt = f"Player says: {prompt}\nDM responds:"

                # Encode input
                inputs = self.tokenizer.encode(enhanced_prompt + self.tokenizer.eos_token, return_tensors="pt")
                if self.device == "cuda":
                    inputs = inputs.to(self.device)

                # Generate response
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        temperature=0.7,
                        top_p=0.9,
                        repetition_penalty=1.1,
                        pad_token_id=self.tokenizer.eos_token_id,
                        early_stopping=True
                    )

                # Decode response
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

                # Extract the DM response part
                if "DM responds:" in response:
                    dm_response = response.split("DM responds:")[-1].strip()
                else:
                    # Fallback - take everything after the original prompt
                    dm_response = response[len(enhanced_prompt):].strip()

                return dm_response

            # Run with timeout
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(_generate_sync),
                    timeout=30.0  # DialoGPT should be much faster than Llama
                )

                # Post-process to catch any D&D rule violations
                response = self._post_process_response(response)

                return response

            except asyncio.TimeoutError:
                logging.warning("DialoGPT generation timed out after 30 seconds, falling back to XAI if available")

                # XAI fallback disabled for testing

                return "The DM considers the situation carefully... (DialoGPT model overloaded, try again shortly)"

        except Exception as e:
            logging.error(f"An error occurred during DialoGPT text generation: {e}")
            return "Sorry, I encountered an error and couldn't process your request."

    def _post_process_response(self, response: str) -> str:
        """
        Post-process response to catch D&D rule violations that the model might still make.
        """
        # Remove common D&D rule violations
        violation_patterns = [
            r"[Hh]e looks (nervous|worried|concerned|suspicious|angry|happy)",
            r"[Ss]he (seems|appears|looks) (nervous|worried|concerned|suspicious|angry|happy)",
            r"[Yy]ou can (see|tell|sense) (that )?[sS]?he is (nervous|worried|concerned|suspicious|angry)",
            r"[Hh]is expression (shows|reveals|betrays)",
            r"[Hh]er eyes (betray|show|reveal)",
            r"[Ww]hat do you (do|propose|want to do)",
            r"[Ww]hat would you like to do",
            r"[Ww]hat's your next move"
        ]

        import re
        for pattern in violation_patterns:
            if re.search(pattern, response):
                logging.info(f"Post-processing caught D&D rule violation: {pattern}")
                # Replace with observable description
                response = re.sub(pattern, "The figure shifts slightly", response)

        return response

# Global instance for testing
llm_manager_dialogpt = LLMManagerDialoGPT()

if __name__ == '__main__':
    # Test script
    import asyncio

    async def test_dialogpt():
        print("Loading DialoGPT model for testing...")
        llm_manager_dialogpt.load_model()

        if llm_manager_dialogpt.model:
            test_prompt = "You enter the tavern. The bartender glances at you."
            print(f"Test prompt: {test_prompt}")
            print("Generating response...")
            response = await llm_manager_dialogpt.generate(test_prompt)
            print(f"DialoGPT Response:\n{response}")
        else:
            print("Could not run test because the DialoGPT model failed to load.")

    asyncio.run(test_dialogpt())