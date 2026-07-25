# src/intent_llm.py
"""Small local LLM: player text → intent JSON only. Never rolls dice or narrates."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Sequence

from .config import settings

logger = logging.getLogger(__name__)


def build_intent_prompt(
    text: str,
    weapon_names: Optional[Sequence[str]] = None,
) -> str:
    weapons = ", ".join(weapon_names) if weapon_names else "(none listed)"
    return (
        "You extract D&D player intent. Reply with ONE JSON object only. No markdown.\n"
        "Keys: action, target, method, weapon_hint, spell_name, needs_clarify, "
        "clarify_prompt, confidence.\n"
        "action: attack|cast|rest|roll|use_item|move|speak|unclear\n"
        "method: unarmed|weapon|improvised|unknown|null\n"
        "Rules:\n"
        "- punch/kick/fist/slap => method=unarmed\n"
        "- named weapon => method=weapon and weapon_hint\n"
        "- attack but unclear how => method=unknown\n"
        "- cast => action=cast and spell_name\n"
        "- pure roleplay/chat => action=speak\n"
        f"Allowed weapon names (hints only): {weapons}\n"
        f'Player: "{text}"\n'
        "JSON:"
    )


class IntentLLM:
    """Dedicated small model for structured intent extraction."""

    def __init__(self) -> None:
        self.pipeline = None
        self.model_name = getattr(
            settings, "INTENT_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct"
        )
        self.device = (getattr(settings, "INTENT_DEVICE", "cpu") or "cpu").lower()
        self.timeout_sec = float(getattr(settings, "INTENT_TIMEOUT_SEC", 12.0) or 12.0)
        self.max_new_tokens = int(getattr(settings, "INTENT_MAX_NEW_TOKENS", 80) or 80)
        self._load_failed = False

    def load(self) -> None:
        if self.pipeline or self._load_failed:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            logger.info(
                "Loading intent model %s on %s ...", self.model_name, self.device
            )
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.device == "cuda" and torch.cuda.is_available():
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                )
                self.pipeline = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device_map="auto",
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float32,
                )
                self.pipeline = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device=-1,
                )
            logger.info("Intent model loaded successfully.")
        except Exception:
            logger.exception("Failed to load intent model %s", self.model_name)
            self.pipeline = None
            self._load_failed = True

    async def generate_intent_json(
        self,
        text: str,
        weapon_names: Optional[Sequence[str]] = None,
    ) -> str:
        """Return raw model text expected to contain a JSON object."""
        prompt = build_intent_prompt(text, weapon_names)
        if not self.pipeline and not self._load_failed:
            await asyncio.to_thread(self.load)
        if not self.pipeline:
            raise RuntimeError("intent model not available")

        def _sync() -> str:
            tokenizer = self.pipeline.tokenizer
            messages = [{"role": "user", "content": prompt}]
            try:
                formatted = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception:
                formatted = prompt

            outputs = self.pipeline(
                formatted,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                return_full_text=True,
                pad_token_id=tokenizer.eos_token_id,
            )
            generated = outputs[0]["generated_text"]
            if generated.startswith(formatted):
                return generated[len(formatted) :].strip()
            return generated.strip()

        return await asyncio.wait_for(
            asyncio.to_thread(_sync),
            timeout=self.timeout_sec,
        )


intent_llm = IntentLLM()
