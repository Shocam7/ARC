"""
ARC Model Registry
──────────────────
Single source of truth for every Gemini model string used across ARC.
Update here to switch models globally.

All models confirmed available on Google AI Studio free tier (Feb 2026).
"""

# ── Real-time voice / Live API ────────────────────────────────────────────────
# Powers the live bidirectional audio session for every AF.
# 2.5 Flash supports the Live API and is significantly smarter than 2.0 Flash Live.
LIVE_MODEL = "gemini-2.5-flash"

# ── Orchestrator routing ──────────────────────────────────────────────────────
# Routes user messages to the correct AF (multi-agent mode).
# Needs to be fast (~200ms) — Flash is ideal.
ORCHESTRATOR_MODEL = "gemini-2.5-flash"

# ── Screen vision / analysis ──────────────────────────────────────────────────
# Analyses screenshots, locates UI elements, understands app context.
# 2.5 Flash has substantially better spatial understanding than 2.0 Flash.
VISION_MODEL = "gemini-2.5-flash"

# ── Computer Use ──────────────────────────────────────────────────────────────
# Dedicated model trained specifically for screen control tasks.
# Receives a screenshot and returns structured actions (click, type, scroll…).
# This is the right tool for: clicking buttons, form-filling, UI navigation.
COMPUTER_USE_MODEL = "gemini-2.5-computer-use-preview-10-2025"

# ── Deep Research ─────────────────────────────────────────────────────────────
# Multi-step research model — performs thorough web research autonomously.
# Use when an AF needs comprehensive, cited research (not quick lookups).
DEEP_RESEARCH_MODEL = "deep-research-pro-preview-12-2025"

# ── Text-to-Speech (supplementary) ───────────────────────────────────────────
# High-quality TTS for responses outside the Live session
# (e.g. tool completion confirmations, long narrations).
TTS_MODEL   = "gemini-2.5-flash-preview-tts"
TTS_PRO_MODEL = "gemini-2.5-pro-preview-tts"

# ── General reasoning / complex tasks ────────────────────────────────────────
# Used for tasks that need deeper reasoning: code generation, analysis, planning.
# Falls back to FLASH_MODEL for simpler tasks to stay within rate limits.
PRO_MODEL   = "gemini-2.5-pro"
FLASH_MODEL = "gemini-2.5-flash"
FLASH_LITE  = "gemini-2.5-flash-lite"

# ── Model capability matrix (for reference) ──────────────────────────────────
MODEL_INFO = {
    LIVE_MODEL:          "Real-time voice, multimodal Live API",
    ORCHESTRATOR_MODEL:  "Fast routing, low latency",
    COMPUTER_USE_MODEL:  "Screen control, UI interaction, action planning",
    DEEP_RESEARCH_MODEL: "Multi-step web research with citations",
    VISION_MODEL:        "Screenshot understanding, spatial reasoning",
    TTS_MODEL:           "High-quality speech synthesis (Flash quality)",
    TTS_PRO_MODEL:       "Studio-quality speech synthesis (Pro quality)",
    PRO_MODEL:           "Complex reasoning, long context, coding",
    FLASH_LITE:          "Ultra-fast, low-cost, simple tasks",
}
