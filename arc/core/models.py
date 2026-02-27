"""
ARC Model Registry — Vertex AI Edition
───────────────────────────────────────
Single source of truth for every Gemini model string used across ARC.
All models are accessed through Vertex AI (Google Cloud), not AI Studio.

Reference: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live
"""

# ── Real-time voice / Live API ────────────────────────────────────────────────
# The Live API on Vertex AI (v1beta1 endpoint).
# This is the Vertex AI-specific Live model ID from official docs.
LIVE_MODEL = "gemini-2.0-flash-live-preview-04-09"

# ── Orchestrator routing ──────────────────────────────────────────────────────
# Fast routing between agents (~150-250ms). Flash is ideal.
ORCHESTRATOR_MODEL = "gemini-2.5-flash"

# ── Screen vision / analysis ──────────────────────────────────────────────────
# Analyses screenshots, locates UI elements, understands application context.
VISION_MODEL = "gemini-2.5-flash"

# ── Computer Use ──────────────────────────────────────────────────────────────
# Dedicated screen-control model. Check Vertex AI Model Garden for availability.
# Falls back to VISION_MODEL if unavailable in your region.
COMPUTER_USE_MODEL = "gemini-2.5-computer-use-preview-04-2025"

# ── Deep Research ─────────────────────────────────────────────────────────────
# Multi-step autonomous web research. Uses Flash + grounding until GA on Vertex.
DEEP_RESEARCH_MODEL = "gemini-2.5-flash"

# ── General purpose ───────────────────────────────────────────────────────────
PRO_MODEL   = "gemini-2.5-pro"
FLASH_MODEL = "gemini-2.5-flash"
FLASH_LITE  = "gemini-2.5-flash-lite"

# ── Text-to-Speech ───────────────────────────────────────────────────────────
TTS_MODEL     = "gemini-2.5-flash-preview-tts"
TTS_PRO_MODEL = "gemini-2.5-pro-preview-tts"

# ── Capability reference ──────────────────────────────────────────────────────
MODEL_INFO = {
    LIVE_MODEL:          "Real-time voice, Vertex AI Live API (v1beta1)",
    ORCHESTRATOR_MODEL:  "Fast routing, generate_content (v1)",
    COMPUTER_USE_MODEL:  "Screen control, structured action output",
    DEEP_RESEARCH_MODEL: "Multi-step web research with citations",
    VISION_MODEL:        "Screenshot understanding, spatial reasoning",
    TTS_MODEL:           "High-quality speech synthesis",
    PRO_MODEL:           "Complex reasoning, long context, coding",
    FLASH_LITE:          "Ultra-fast, low-cost simple tasks",
}