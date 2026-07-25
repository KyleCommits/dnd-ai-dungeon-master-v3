# src/llm_manager.py
"""
Local transformers LLM manager — sole DM runtime (no Gemini for chat).
"""
import logging
import torch
from typing import List, Dict, Any, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, AutoConfig
from .config import settings

TOOL_CALL_PROTOCOL = """
TOOL CALLING PROTOCOL (mandatory when you need to change game state):
Emit one or more blocks exactly like this (JSON on one line between markers):

TOOL_CALL
{"name": "function_name", "arguments": {"arg1": "value"}}
END_TOOL_CALL

Rules:
- Only use listed available functions.
- Only executed TOOL_CALL blocks change game state. Do not invent HP/dice results in prose without a tool call.
- After tool calls, you may write brief narration; the system will re-ask you to narrate with real results if needed.
"""


class LLMManager:
    def __init__(self):
        self.pipeline = None
        self.model_name = settings.LOCAL_MODEL_NAME
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Gemini intentionally unused for DM chat (local-only policy)
        self.gemini_client = None
        logging.info(f"LLMManager initialized — local-only DM on {self.device}, model={self.model_name}")

    def load_model(self):
        """Loads the Hugging Face model and tokenizer."""
        if self.pipeline:
            logging.info("Model is already loaded.")
            return

        try:
            logging.info(f"Loading model: {self.model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True
            )

            config = AutoConfig.from_pretrained(self.model_name, trust_remote_code=True)
            if hasattr(config, "rope_scaling") and isinstance(config.rope_scaling, dict):
                if 'rope_type' in config.rope_scaling:
                    logging.warning("Adapting Llama 3.1 rope_scaling config for current transformers version.")
                    config.rope_scaling['type'] = config.rope_scaling.get('rope_type', 'llama3')
                    if 'rope_type' in config.rope_scaling:
                        del config.rope_scaling['rope_type']
                    logging.info(f"Fixed rope_scaling: {config.rope_scaling}")

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

    def _format_functions_for_prompt(self, functions: List[Dict]) -> str:
        """format function definitions for prompt inclusion"""
        function_descriptions = []
        for func in functions:
            name = func['name']
            desc = func['description']
            params = func['parameters'].get('required', [])
            function_descriptions.append(f"- {name}({', '.join(params)}): {desc}")
        return '\n'.join(function_descriptions)

    def build_prompt_with_tools(self, prompt: str, available_functions: Optional[List[Dict]] = None) -> str:
        """Append tool protocol + function list for local generation."""
        if not available_functions:
            return prompt
        return (
            f"{prompt}\n\n"
            f"AVAILABLE FUNCTIONS:\n{self._format_functions_for_prompt(available_functions)}\n"
            f"{TOOL_CALL_PROTOCOL}"
        )

    async def generate(
        self,
        prompt: str,
        max_new_tokens: int = 600,
        use_massive_context: bool = True,
        available_functions: List[Dict] = None,
    ) -> str:
        """
        Local-only DM generation. Gemini is never used for chat.
        use_massive_context is accepted for API compatibility but does not route to cloud.
        """
        full_prompt = self.build_prompt_with_tools(prompt, available_functions)
        logging.info("Using local transformers pipeline for DM generation")
        return await self._generate_local(full_prompt, max_new_tokens)

    async def _generate_local(self, prompt: str, max_new_tokens: int = 200) -> str:
        """Local LLM generation (primary path)."""
        if not self.pipeline:
            logging.error("Pipeline is not initialized. Cannot generate text.")
            return (
                "The DM's mind is clouded and cannot respond. "
                "The local AI model failed to initialize. Please restart the system."
            )

        messages = [{"role": "user", "content": prompt}]

        try:
            import asyncio

            def _generate_sync():
                formatted_prompt = self.pipeline.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )

                outputs = self.pipeline(
                    formatted_prompt,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.pipeline.tokenizer.eos_token_id
                )
                return outputs

            try:
                outputs = await asyncio.wait_for(
                    asyncio.to_thread(_generate_sync),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                logging.error("Local LLM generation timed out after 60 seconds")
                return (
                    "The DM takes too long to consider the situation and falls silent. "
                    "The local model timed out after 60 seconds. Please try again."
                )

            generated_text = outputs[0]["generated_text"]

            formatted_prompt = self.pipeline.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            if generated_text.startswith(formatted_prompt):
                response = generated_text[len(formatted_prompt):].strip()
            else:
                user_content = messages[-1]['content']
                if user_content in generated_text:
                    last_user_pos = generated_text.rfind(user_content)
                    response = generated_text[last_user_pos + len(user_content):].strip()
                else:
                    response = generated_text.strip()

            response = response.replace("<|im_end|>", "").replace("<|eot_id|>", "").strip()
            return response

        except Exception as e:
            logging.error(f"An error occurred during local text generation: {e}")
            return (
                "The DM stumbles over their words and cannot continue. "
                "A generation error occurred. Please try again."
            )


llm_manager = LLMManager()

if __name__ == '__main__':
    import asyncio
    try:
        print("Loading model for testing...")
        llm_manager.load_model()

        if llm_manager.pipeline:
            prompt = "You are a master storyteller. Narrate a brief, thrilling moment from a fantasy adventure."
            print("Generating response...")
            response = asyncio.run(llm_manager.generate(prompt))
            print(f"Generated Response:\n{response}")
        else:
            print("Could not run test because the model failed to load.")

    except Exception as e:
        logging.error(f"An error occurred during LLMManager testing: {e}")
