import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class LlmClient:
    """Wrapper class to communicate with Gemini, OpenAI, or local models."""
    
    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        self.model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
        
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("API_BASE_URL") # Custom endpoint (e.g., OpenRouter, Ollama)
        
        self.genai_client = None
        self.openai_client = None
        
        self._init_client()
        
    def _init_client(self):
        if self.provider == "gemini":
            if not self.gemini_key:
                # Fallback to check if openai key is configured for custom endpoint
                if self.openai_key:
                    self.provider = "openai"
                else:
                    raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            
            if self.provider == "gemini":
                try:
                    from google import genai
                    self.genai_client = genai.Client(api_key=self.gemini_key)
                except ImportError:
                    # Fallback to openai wrapper if google-genai package is not available
                    from openai import OpenAI
                    base_url = "https://generativelanguage.googleapis.com/v1beta/"
                    self.openai_client = OpenAI(api_key=self.gemini_key, base_url=base_url)
                    self.provider = "gemini_openai_fallback"
                    
        elif self.provider == "openai":
            if not self.openai_key:
                raise ValueError("OPENAI_API_KEY is not set in environment variables.")
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=self.openai_key,
                base_url=self.api_base if self.api_base else None
            )
            
        elif self.provider == "custom" or self.api_base:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=self.openai_key or "sk-dummy-key",
                base_url=self.api_base
            )
            
    def generate(self, system_instruction: str, prompt: str, stop_sequences: Optional[List[str]] = None) -> str:
        """Generates a text completion given system instructions and user prompt."""
        if self.provider == "gemini" and self.genai_client:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                stop_sequences=stop_sequences,
                temperature=0.2,
            )
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return response.text or ""
            
        elif self.provider == "gemini_openai_fallback" and self.openai_client:
            # Google Generative Language OpenAI compatibility
            # Needs models/ prefix or specific name
            model = self.model_name
            if not model.startswith("models/"):
                model = f"models/{model}"
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                stop=stop_sequences,
                temperature=0.2
            )
            return response.choices[0].message.content or ""
            
        elif self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                stop=stop_sequences,
                temperature=0.2
            )
            return response.choices[0].message.content or ""
            
        else:
            raise ValueError("No API client initialized. Check your credentials.")
