"""Local secrets loading — never commit keys; never send keys to the cloud."""

from ada.secrets.load import MissingSecret, load_gemini_api_key

__all__ = ["MissingSecret", "load_gemini_api_key"]
