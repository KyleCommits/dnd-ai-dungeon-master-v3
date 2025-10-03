# src/llm_manager.py
import logging
import torch
from typing import List, Dict, Any
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, AutoConfig
from groq import Groq
import google.generativeai as genai
from .config import settings

class LLMManager:
    def __init__(self):
        self.pipeline = None
        self.model_name = settings.LOCAL_MODEL_NAME
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # setup gemini as main dm brain
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel('gemini-2.5-flash-lite')
                logging.info("Gemini 2.5 Flash-Lite initialized successfully as primary DM (cost-optimized)")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini 2.5 Flash-Lite: {e}")

        # xai stuff commented out for now
        # self.xai_client = None
        # if settings.XAI_API_KEY:
        #     # clean up the api key
        #     clean_api_key = settings.XAI_API_KEY.strip().strip('"').strip("'")
        #     logging.info(f"Initializing XAI client with API key length: {len(clean_api_key)}")
        #     self.xai_client = Groq(api_key=clean_api_key, base_url="https://api.x.ai/v1")

        logging.info(f"LLMManager initialized - Gemini: {'✅' if self.gemini_client else '❌'}, Local: {self.device}")

    def load_model(self):
        """Loads the Hugging Face model and tokenizer."""
        if self.pipeline:
            logging.info("Model is already loaded.")
            return

        try:
            logging.info(f"Loading model: {self.model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # setup 8-bit quantization for speed
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True  # Allow CPU offload if needed
            )
            
            # load model config and fix rope scaling
            config = AutoConfig.from_pretrained(self.model_name, trust_remote_code=True)
            if hasattr(config, "rope_scaling") and isinstance(config.rope_scaling, dict):
                if 'rope_type' in config.rope_scaling:
                    logging.warning("Adapting Llama 3.1 rope_scaling config for current transformers version.")
                    # newer transformers need type field
                    config.rope_scaling['type'] = config.rope_scaling.get('rope_type', 'llama3')
                    # remove old rope_type field
                    if 'rope_type' in config.rope_scaling:
                        del config.rope_scaling['rope_type']
                    logging.info(f"Fixed rope_scaling: {config.rope_scaling}")

            # load model with quantization
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                config=config,
                torch_dtype=torch.float16,
                device_map="auto",
                quantization_config=quantization_config,
                trust_remote_code=True,
                ignore_mismatched_sizes=True
            )
            
            self.pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device_map="auto"
            )
            logging.info("Model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load the model: {e}")
            self.pipeline = None

    async def generate(self, prompt: str, max_new_tokens: int = 600, use_massive_context: bool = True,
                       available_functions: List[Dict] = None) -> str:
        """
        V1 Strategy: Use Gemini Pro with massive context for proper D&D rule enforcement.
        Falls back to local LLM only if Gemini fails.
        """

        # main approach - gemini flash with big context
        if self.gemini_client and use_massive_context:
            try:
                logging.info("Using Gemini 2.5 Flash-Lite with massive context (V1 approach, cost-optimized)")

                if available_functions:
                    # todo: implement proper function calling when gemini api is updated
                    # for now just do regular generation with function hints
                    enhanced_prompt = f"""{prompt}

AVAILABLE FUNCTIONS (for reference - describe what you would do):
{self._format_functions_for_prompt(available_functions)}
"""
                    response = self.gemini_client.generate_content(enhanced_prompt)
                    return response.text.strip()
                else:
                    # regular generation
                    response = self.gemini_client.generate_content(prompt)
                    return response.text.strip()
            except Exception as e:
                logging.error(f"Gemini 2.5 Flash-Lite failed: {e}, falling back to local LLM")

        # Fallback: Local LLM (current V3 implementation)
        return await self._generate_local(prompt, max_new_tokens)

    def _format_functions_for_prompt(self, functions: List[Dict]) -> str:
        """format function definitions for prompt inclusion"""
        function_descriptions = []
        for func in functions:
            name = func['name']
            desc = func['description']
            params = func['parameters'].get('required', [])
            function_descriptions.append(f"- {name}({', '.join(params)}): {desc}")
        return '\n'.join(function_descriptions)


    async def _generate_local(self, prompt: str, max_new_tokens: int = 200) -> str:
        """
        Local LLM generation (fallback only).
        """
        if not self.pipeline:
            logging.error("Pipeline is not initialized. Cannot generate text.")
            return "The DM's mind is clouded and cannot respond. The local AI model failed to initialize. Please restart the system."

        messages = [{"role": "user", "content": prompt}]

        try:
            # Run the potentially slow LLM generation in a thread with timeout
            import asyncio

            def _generate_sync():
                # The pipeline expects a specific format, often just the prompt string
                # For chat models, we can format it using the tokenizer's chat template
                formatted_prompt = self.pipeline.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )

                outputs = self.pipeline(
                    formatted_prompt,
                    max_new_tokens=max_new_tokens,  # Use the requested token count
                    do_sample=True,
                    temperature=0.7,  # Balanced creativity vs speed
                    top_p=0.9,        # Slightly wider sampling for speed
                    repetition_penalty=1.1,  # Prevent repetition
                    pad_token_id=self.pipeline.tokenizer.eos_token_id
                    # early_stopping removed - deprecated parameter
                )
                return outputs

            # Run with timeout - increased for web system
            try:
                outputs = await asyncio.wait_for(
                    asyncio.to_thread(_generate_sync),
                    timeout=60.0  # Increased timeout for web system (no Discord heartbeat limit)
                )
            except asyncio.TimeoutError:
                logging.error("Local LLM generation timed out after 60 seconds")
                return "The DM takes too long to consider the situation and falls silent. The local model timed out after 60 seconds. Please try again."

            generated_text = outputs[0]["generated_text"]

            # Find where the actual response starts after the formatted prompt
            formatted_prompt = self.pipeline.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            if generated_text.startswith(formatted_prompt):
                response = generated_text[len(formatted_prompt):].strip()
            else:
                # Try simpler approach - just take everything after the user's message
                user_content = messages[-1]['content']
                if user_content in generated_text:
                    # Find the last occurrence of user content and take everything after
                    last_user_pos = generated_text.rfind(user_content)
                    response = generated_text[last_user_pos + len(user_content):].strip()
                else:
                    # Fallback - use the whole generated text
                    response = generated_text.strip()

            # Clean up any remaining template tokens
            response = response.replace("<|im_end|>", "").replace("<|eot_id|>", "").strip()
            return response

        except Exception as e:
            logging.error(f"An error occurred during local text generation: {e}")
            return "The DM stumbles over their words and cannot continue. A generation error occurred. Please try again."

# Global instance to be used by the application
llm_manager = LLMManager()

if __name__ == '__main__':
    # Example usage for direct testing
    try:
        print("Loading model for testing...")
        llm_manager.load_model() # Explicitly load the model for the test
        
        if llm_manager.pipeline:
            prompt = "You are a master storyteller. Narrate a brief, thrilling moment from a fantasy adventure."
            print("Generating response...")
            response = llm_manager.generate(prompt)
            print(f"Generated Response:\n{response}")
        else:
            print("Could not run test because the model failed to load.")
            
    except Exception as e:
        logging.error(f"An error occurred during LLMManager testing: {e}")

