"""Central configuration and environment management for the AI text-to-video pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from workspace root if present
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _WORKSPACE_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


def get_gemini_api_keys() -> list[str]:
    """Retrieve all configured Gemini API keys in priority order for chained failover/rotation."""
    keys: list[str] = []
    for var_name in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GOOGLE_API_KEY"]:
        val = os.getenv(var_name)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())
    return keys


def get_gemini_api_key() -> str | None:
    """Retrieve primary Gemini API key from environment."""
    keys = get_gemini_api_keys()
    return keys[0] if keys else None


def get_openai_api_key() -> str | None:
    """Retrieve OpenAI API key from environment."""
    return os.getenv("OPENAI_API_KEY")


def get_runpod_api_key() -> str | None:
    """Retrieve RunPod API key from environment."""
    return os.getenv("RUNPOD_API_KEY")


def get_together_api_key() -> str | None:
    """Retrieve Together AI API key from environment."""
    return os.getenv("TOGETHER_API_KEY")


def get_cloudflare_credentials() -> tuple[str | None, str | None]:
    """Retrieve Cloudflare Account ID and API Token from environment."""
    acc = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    tok = os.getenv("CLOUDFLARE_API_TOKEN")
    return (acc.strip() if acc else None, tok.strip() if tok else None)


def get_puter_api_key() -> str | None:
    """Retrieve Puter API key / Auth Token from environment."""
    tok = os.getenv("PUTER_API_KEY")
    return tok.strip() if tok and tok.strip() and not tok.strip().startswith("your_") else None



def get_default_llm_timeout() -> float:
    """Retrieve default LLM request timeout in seconds."""
    return float(os.getenv("LLM_TIMEOUT_SEC", "10.0"))


def get_comfy_timeout_sec() -> int:
    """Retrieve ComfyUI / diffusion timeout in seconds (default 900s = 15m)."""
    return int(os.getenv("COMFY_TIMEOUT_SEC", "900"))


def get_runpod_serverless_endpoint_id() -> str | None:
    """Retrieve RunPod Serverless Endpoint ID from environment."""
    return os.getenv("RUNPOD_SERVERLESS_ENDPOINT_ID")


def get_max_serverless_concurrency() -> int:
    """Retrieve maximum concurrent serverless workers (default 4)."""
    return int(os.getenv("MAX_SERVERLESS_CONCURRENCY", "4"))
