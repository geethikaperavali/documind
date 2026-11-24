import json
import re
import time
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from backend.config import settings

class GeminiGateway:
    """
    Centralized Gateway for Google Gemini AI.
    Provides:
    - Resilient failover across candidate models
    - Robust JSON extraction & cleanup (strips markdown code blocks)
    - Optional per-request API key overrides
    - Performance logging & error recovery
    """

    DEFAULT_FALLBACK_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]

    def __init__(self):
        self._default_client: Optional[genai.Client] = None

    def _get_client(self, api_key: Optional[str] = None) -> genai.Client:
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured in environment or request.")
        
        # If using server default key, cache the client
        if not api_key:
            if self._default_client is None:
                self._default_client = genai.Client(api_key=key)
            return self._default_client
        
        return genai.Client(api_key=key)

    def _get_candidate_models(self) -> List[str]:
        models = []
        if settings.GEMINI_MODEL and settings.GEMINI_MODEL not in models:
            models.append(settings.GEMINI_MODEL)
        for m in self.DEFAULT_FALLBACK_MODELS:
            if m not in models:
                models.append(m)
        return models

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        api_key: Optional[str] = None
    ) -> str:
        """
        Generates text using Gemini with automatic model failover.
        """
        client = self._get_client(api_key=api_key)
        models = self._get_candidate_models()
        last_error = None

        config_args = {"temperature": temperature}
        if system_instruction:
            config_args["system_instruction"] = system_instruction
        config = types.GenerateContentConfig(**config_args)

        for model in models:
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                last_error = e
                # Transient error: continue to next model in fallback list
                continue

        raise RuntimeError(f"All Gemini models failed for text generation. Last error: {last_error}")

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        api_key: Optional[str] = None,
        default_fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates structured JSON using Gemini response_mime_type with robust parsing.
        """
        client = self._get_client(api_key=api_key)
        models = self._get_candidate_models()
        last_error = None

        config_args = {
            "temperature": temperature,
            "response_mime_type": "application/json"
        }
        if system_instruction:
            config_args["system_instruction"] = system_instruction
        config = types.GenerateContentConfig(**config_args)

        for model in models:
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                if resp and resp.text:
                    text = resp.text.strip()
                    # Strip any markdown code fences if model enclosed JSON
                    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
                    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE).strip()
                    return json.loads(text)
            except Exception as e:
                last_error = e
                continue

        if default_fallback is not None:
            return default_fallback
        raise RuntimeError(f"All Gemini models failed for JSON generation. Last error: {last_error}")

gemini_gateway = GeminiGateway()
