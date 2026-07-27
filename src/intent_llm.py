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
    npc_names: Optional[Sequence[str]] = None,
) -> str:
    weapons = ", ".join(weapon_names) if weapon_names else "(none listed)"
    npcs = ", ".join(npc_names) if npc_names else "(none listed)"
    return (
        "You extract D&D player intent. Reply with ONE JSON object only. No markdown.\n"
        "Keys: action, target, method, weapon_hint, spell_name, needs_clarify, "
        "clarify_prompt, confidence.\n"
        "action: attack|cast|rest|roll|use_item|move|speak|repeat_last|unclear\n"
        "method: unarmed|weapon|improvised|unknown|null\n"
        "Rules:\n"
        "- greetings, questions, flirtation, look around => speak\n"
        "- 'i say …', 'i tell …', quoted dialogue => ALWAYS speak\n"
        "- apologies, offering gold, talking about PAST damage => speak\n"
        "- Mentioning tables/weapons inside conversation is NOT an attack\n"
        "- attack ONLY if the player is trying to hit something RIGHT NOW\n"
        "- punch/kick/fist/slap => attack method=unarmed\n"
        "- 'i attack the X' => attack (method=null if no weapon named)\n"
        "- named NPC as live attack target => attack that name\n"
        "- try again / and again / once more => repeat_last\n"
        "- cast => cast + spell_name\n"
        # Input first, output second. Written the other way round the model never
        # sees an input-to-output mapping, only a list of JSON blobs.
        "Examples:\n"
        'Player: "hello!"\nJSON: {"action":"speak","confidence":0.95}\n'
        'Player: "i say hello"\nJSON: {"action":"speak","confidence":0.95}\n'
        'Player: "im sorry i destroyed your tables. will 1000 gold cover it?"\n'
        'JSON: {"action":"speak","confidence":0.95}\n'
        'Player: "i say \\"sorry about the tables\\""\n'
        'JSON: {"action":"speak","confidence":0.95}\n'
        'Player: "i attack the table"\n'
        'JSON: {"action":"attack","target":"table","method":null,"confidence":0.9}\n'
        'Player: "i attack Mira"\n'
        'JSON: {"action":"attack","target":"Mira","method":null,"confidence":0.9}\n'
        'Player: "try again"\nJSON: {"action":"repeat_last","confidence":0.95}\n'
        f"Allowed weapon names (hints): {weapons}\n"
        f"Known NPCs (hints): {npcs}\n"
        f'Player: "{text}"\n'
        "JSON:"
    )


class IntentLLM:
    """Dedicated small model for structured intent extraction."""

    def __init__(self) -> None:
        self.pipeline = None
        self.model_name = getattr(
            settings, "INTENT_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct"
        )
        self.device = (getattr(settings, "INTENT_DEVICE", "cpu") or "cpu").lower()
        self.timeout_sec = float(getattr(settings, "INTENT_TIMEOUT_SEC", 20.0) or 20.0)
        self.max_new_tokens = int(getattr(settings, "INTENT_MAX_NEW_TOKENS", 100) or 100)
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
            logger.info(
                "IntentLLM ready on %s (by design; DM narrator stays on GPU) model=%s",
                self.device,
                self.model_name,
            )
        except Exception:
            logger.exception("Failed to load intent model %s", self.model_name)
            self.pipeline = None
            self._load_failed = True

    async def generate_intent_json(
        self,
        text: str,
        weapon_names: Optional[Sequence[str]] = None,
        npc_names: Optional[Sequence[str]] = None,
    ) -> str:
        """Return raw model text expected to contain a JSON object."""
        prompt = build_intent_prompt(text, weapon_names, npc_names)
        if not self.pipeline and not self._load_failed:
            await asyncio.to_thread(self.load)
        if not self.pipeline:
            raise RuntimeError("Intent model unavailable")

        def _run() -> str:
            tokenizer = self.pipeline.tokenizer
            messages = [{"role": "user", "content": prompt}]
            if hasattr(tokenizer, "apply_chat_template"):
                formatted = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            else:
                formatted = prompt
            outputs = self.pipeline(
                formatted,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                return_full_text=True,
                pad_token_id=tokenizer.eos_token_id,
            )
            full = outputs[0]["generated_text"]
            if full.startswith(formatted):
                return full[len(formatted) :].strip()
            return full.strip()

        return await asyncio.wait_for(
            asyncio.to_thread(_run),
            timeout=self.timeout_sec,
        )


intent_llm = IntentLLM()
