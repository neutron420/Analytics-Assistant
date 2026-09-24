"""
Hugging Face Inference Providers Translation Provider
Translation Quality Analytics & Continuous Improvement Platform

Default provider connecting to Hugging Face Inference Providers using HF_TOKEN.
Formats structured prompts requesting Literal, Natural, and Formal styles in JSON.
"""

import json
import logging
import re
import time
from typing import List, Optional, Tuple
from uuid import uuid4

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from src.config import config
from src.translation.models import TranslationOptionDTO
from src.translation.providers.base import BaseTranslationProvider

logger = logging.getLogger("hf_provider")

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "bn": "Bengali",
    "ja": "Japanese",
}


class HuggingFaceTranslationProvider(BaseTranslationProvider):
    """Translation provider backed by Hugging Face Inference Providers."""

    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self.token = token or config.hf_token
        self.model = model or config.hf_model
        
        if not self.token:
            logger.warning("HF_TOKEN is not set; HuggingFaceTranslationProvider will fail on live calls.")
        
        # Initialize client with token
        self.client = InferenceClient(token=self.token)

    @property
    def provider_name(self) -> str:
        return "huggingface"

    def _build_system_prompt(self, src_lang_name: str, tgt_lang_name: str) -> str:
        return (
            f"You are an expert multilingual translation engine specializing in translating from {src_lang_name} to {tgt_lang_name}.\n"
            "Translate the source text into three distinct styles:\n"
            "1. LITERAL: Direct, syntax-faithful lexical translation preserving word order where possible.\n"
            "2. NATURAL: Fluent, everyday idiomatic translation as spoken by native speakers.\n"
            "3. FORMAL: Polite, elevated, grammatically precise translation appropriate for professional/official contexts.\n\n"
            "You MUST respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "translations": [\n'
            '    {"style": "LITERAL", "text": "..."},\n'
            '    {"style": "NATURAL", "text": "..."},\n'
            '    {"style": "FORMAL", "text": "..."}\n'
            "  ],\n"
            '  "confidence": 0.95\n'
            "}\n"
            "Strict rules:\n"
            "- Output valid JSON only. Do not add markdown code fences (```json) or conversational preamble.\n"
            "- Accurately preserve named entities, numbers, and technical terms."
        )

    def _extract_json(self, raw_text: str) -> dict:
        """Robustly extracts and parses JSON even if wrapped in conversational text or markdown fences."""
        cleaned = raw_text.strip()
        # Remove markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: search for first '{' to last '}'
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Could not parse valid JSON from provider output: {raw_text[:200]}")

    def generate_translations(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        styles: List[str]
    ) -> Tuple[List[TranslationOptionDTO], Optional[float]]:
        if not self.token:
            raise ValueError("HF_TOKEN is missing. Set HF_TOKEN in environment or .env file.")

        src_name = LANGUAGE_NAMES.get(source_lang.lower(), source_lang)
        tgt_name = LANGUAGE_NAMES.get(target_lang.lower(), target_lang)

        system_prompt = self._build_system_prompt(src_name, tgt_name)
        user_prompt = f"<source_text>\n{source_text.strip()}\n</source_text>"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Execute with exponential backoff retry on HTTP 429 / 503
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat_completion(
                    messages=messages,
                    model=self.model,
                    max_tokens=1000,
                    temperature=0.3
                )
                
                raw_content = response.choices[0].message.content
                parsed_data = self._extract_json(raw_content)

                raw_translations = parsed_data.get("translations", [])
                overall_confidence = float(parsed_data.get("confidence", 0.90))
                # Clamp confidence
                overall_confidence = max(0.0, min(1.0, overall_confidence))

                # Map extracted styles to TranslationOptionDTO
                options: List[TranslationOptionDTO] = []
                found_styles = {}

                for item in raw_translations:
                    s = item.get("style", "").upper()
                    t = item.get("text", "").strip()
                    if s and t:
                        found_styles[s] = t

                for style in styles:
                    text_val = found_styles.get(style, "")
                    if not text_val:
                        # Fallback to any available style or natural
                        text_val = found_styles.get("NATURAL") or list(found_styles.values())[0] if found_styles else source_text

                    options.append(
                        TranslationOptionDTO(
                            option_id=uuid4(),
                            style_option=style,  # type: ignore
                            translated_text=text_val,
                            confidence_score=overall_confidence,
                            user_selected=False
                        )
                    )

                return options, overall_confidence

            except HfHubHTTPError as e:
                status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
                logger.warning(f"HF Inference attempt {attempt + 1}/{max_retries} failed with status {status_code}: {e}")
                last_error = e
                if status_code in (429, 503, 504):
                    time.sleep(1.0 * (2 ** attempt))
                else:
                    raise e
            except Exception as e:
                logger.warning(f"HF Inference attempt {attempt + 1}/{max_retries} error: {e}")
                last_error = e
                time.sleep(1.0)

        raise RuntimeError(f"Hugging Face translation failed after {max_retries} attempts: {last_error}")
