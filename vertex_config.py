"""
vertex_config.py — Centralised Vertex AI client factory.

All ARC modules obtain their genai.Client from here.
Never create a genai.Client inline; always call make_live_client()
or make_standard_client().

Authentication (Application Default Credentials — ADC)
───────────────────────────────────────────────────────
Vertex AI uses Google Cloud ADC, NOT a simple API key.
The SDK resolves credentials in this order:

  1. GOOGLE_APPLICATION_CREDENTIALS env var
     → path to a Service Account JSON key file
     → recommended for production / background daemons

  2. gcloud Application Default Credentials
     → obtained by running once in a terminal:
         gcloud auth application-default login
     → stored in  ~/.config/gcloud/application_default_credentials.json
     → great for local development

  3. Attached service account (Cloud Run, GCE, GKE, etc.)

Required environment variables (.env):
  GOOGLE_CLOUD_PROJECT   — your GCP project ID
  GOOGLE_CLOUD_LOCATION  — region, e.g. us-central1 or global

Optional:
  GOOGLE_APPLICATION_CREDENTIALS  — path to SA JSON key
                                    (only needed if not using gcloud auth)
"""

import logging
import os
from functools import lru_cache

from google import genai
from google.genai.types import HttpOptions

logger = logging.getLogger("arc.vertex_config")

# ── Env-var helpers ───────────────────────────────────────────────────────────

def get_project() -> str:
    """Read GOOGLE_CLOUD_PROJECT from environment."""
    v = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not v:
        raise EnvironmentError(
            "GOOGLE_CLOUD_PROJECT is not set. "
            "Add it to your .env file (see .env.example)."
        )
    return v


def get_location() -> str:
    """Read GOOGLE_CLOUD_LOCATION from environment (defaults to us-central1)."""
    return os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1").strip()


def validate_config() -> tuple[bool, str]:
    """
    Check that required Vertex AI configuration is present.
    Returns (ok: bool, message: str).
    """
    project  = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip()

    if not project:
        return False, (
            "GOOGLE_CLOUD_PROJECT is not set.\n\n"
            "Add it to your .env file:\n"
            "  GOOGLE_CLOUD_PROJECT=your-gcp-project-id\n\n"
            "Then authenticate:\n"
            "  gcloud auth application-default login"
        )
    if not location:
        return False, (
            "GOOGLE_CLOUD_LOCATION is not set.\n\n"
            "Add it to your .env file:\n"
            "  GOOGLE_CLOUD_LOCATION=us-central1"
        )
    return True, f"Vertex AI configured: project={project}, location={location}"


# ── Client factories ──────────────────────────────────────────────────────────

def make_client(api_version: str = "v1") -> genai.Client:
    """
    Create a Vertex AI genai.Client.

    Uses Application Default Credentials (ADC) automatically —
    no api_key parameter required.

    Args:
        api_version: "v1" for standard calls, "v1beta1" for Live API.
    """
    project  = get_project()
    location = get_location()

    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
        http_options=HttpOptions(api_version=api_version),
    )
    logger.debug(
        f"Vertex AI client created: project={project}, "
        f"location={location}, api_version={api_version}"
    )
    return client


def make_live_client() -> genai.Client:
    """
    Create a client configured for the Gemini Live API.
    Live API requires api_version='v1beta1'.
    """
    return make_client(api_version="v1beta1")


def make_standard_client() -> genai.Client:
    """
    Create a client for standard generate_content / embedding calls.
    Uses the stable v1 API.
    """
    return make_client(api_version="v1")