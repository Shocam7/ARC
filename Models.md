# ARC Model Registry

Every Gemini model used in ARC, with its role and why it was chosen.

## Active Models

| Role | Model | Why |
|---|---|---|
| **Real-time voice (Live API)** | `gemini-2.5-flash` | Latest Live-capable model; smarter than 2.0 Flash Live, lower latency than Pro |
| **Orchestrator routing** | `gemini-2.5-flash` | Fast (~200ms), accurate multi-agent routing |
| **Screen vision / analysis** | `gemini-2.5-flash` | Best spatial understanding + OCR for UI analysis |
| **Computer control** | `gemini-2.5-computer-use-preview-10-2025` | Purpose-built for screen control; returns structured actions |
| **Deep research** | `deep-research-pro-preview-12-2025` | Multi-step autonomous web research with citations |
| **TTS (supplementary)** | `gemini-2.5-flash-preview-tts` | High-quality voice for non-Live text responses |
| **Fallback / simple tasks** | `gemini-2.5-flash-lite` | Ultra-fast, low-cost for trivial operations |

All configured in `arc/core/models.py` — change model strings there to switch globally.

## Model Decision Guide for AF Tool Use

```
User asks: "Search for X"        →  search_google (Selenium, free)
User asks: "Research X in depth" →  deep_research (deep-research-pro)
User asks: "Is X true?"          →  fact_check (Flash + Google Search grounding)
User asks: "What's on my screen?"→  look_at_screen (gemini-2.5-flash vision)
User asks: "Click the Save button"→  click_element (Computer Use model)
User asks: "Fill in this form"   →  computer_use (Computer Use model, multi-step)
User asks: "Type this text"      →  type_text (pyautogui, local)
```

## Why NOT gemini-2.5-pro for everything?

Pro is more powerful but:
- ~3-5× higher latency (bad for real-time voice)
- Lower free-tier rate limits
- Overkill for routing/vision tasks

Pro is reserved for future: complex code generation, long-document analysis.
