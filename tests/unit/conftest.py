import os

# Force test mode before backend.core.config's Settings() singleton is ever
# instantiated (first import, triggered by test modules importing backend.main).
# Without this, a real GEMINI_API_KEY leaking in from a developer's local .env
# (python-dotenv's load_dotenv() walks upward from this file's directory) makes
# tests that don't explicitly mock get_genai_client silently call the live
# Gemini API instead of getting deterministic None/fallback behavior.
os.environ.setdefault("ENVIRONMENT", "test")
