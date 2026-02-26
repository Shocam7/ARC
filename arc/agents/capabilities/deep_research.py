"""
DeepResearchCapability — Multi-step autonomous web research via
deep-research-pro-preview-12-2025.

Unlike search_google (which fetches one page), Deep Research:
- Plans a multi-step research strategy
- Searches multiple sources autonomously
- Synthesises findings into a comprehensive, cited report
- Takes 30–120 seconds but produces thorough results

Use when the AF needs to genuinely research a topic, not just
look something up quickly.
"""

import logging
import time

logger = logging.getLogger("arc.capabilities.deep_research")

from arc.core.models import DEEP_RESEARCH_MODEL, FLASH_MODEL


class DeepResearchCapability:
    """
    Wraps the Deep Research Pro model for thorough multi-step research.
    Falls back to Gemini Flash with web search if Deep Research is unavailable.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"DeepResearch client init: {e}")

    def research(self, query: str, depth: str = "standard") -> str:
        """
        Conduct deep multi-step web research on a topic.

        Args:
            query: What to research. Be as specific as possible.
            depth: "quick" (1-2 min), "standard" (2-4 min), "thorough" (4-8 min).
        Returns:
            A comprehensive research report with sources.
        """
        if not self._client:
            return "Deep Research not available (no API key)."

        logger.info(f"DeepResearch: starting research on: {query[:80]}")
        start = time.time()

        # Token budgets by depth
        depth_config = {
            "quick":    {"thinking_budget": 1024,  "max_output": 2048},
            "standard": {"thinking_budget": 4096,  "max_output": 4096},
            "thorough": {"thinking_budget": 8192,  "max_output": 8192},
        }
        cfg = depth_config.get(depth, depth_config["standard"])

        # Research prompt
        prompt = f"""
Please conduct thorough research on the following topic:

{query}

Research requirements:
- Search multiple authoritative sources
- Verify key facts across sources  
- Identify any conflicting information
- Provide a structured report with:
  1. Executive summary (2-3 sentences)
  2. Key findings (bullet points)
  3. Detailed analysis
  4. Sources and citations
  5. Confidence level for key claims

Be comprehensive and accurate. Cite all sources.
""".strip()

        try:
            from google.genai import types as gt

            # Try Deep Research model first
            try:
                response = self._client.models.generate_content(
                    model=DEEP_RESEARCH_MODEL,
                    contents=prompt,
                    config=gt.GenerateContentConfig(
                        tools=[gt.Tool(google_search=gt.GoogleSearch())],
                        max_output_tokens=cfg["max_output"],
                    )
                )
                result = response.text or "No research results returned."
            except Exception as deep_err:
                logger.warning(f"Deep Research model unavailable, falling back to Flash+Search: {deep_err}")
                # Fallback: Flash + Google Search grounding
                response = self._client.models.generate_content(
                    model=FLASH_MODEL,
                    contents=prompt,
                    config=gt.GenerateContentConfig(
                        tools=[gt.Tool(google_search=gt.GoogleSearch())],
                        max_output_tokens=cfg["max_output"],
                        temperature=0.3,
                    )
                )
                result = response.text or "No research results returned."

            elapsed = time.time() - start
            logger.info(f"DeepResearch: completed in {elapsed:.1f}s")
            return f"[Research completed in {elapsed:.1f}s]\n\n{result}"

        except Exception as e:
            logger.error(f"DeepResearch failed: {e}")
            return f"Research error: {e}"

    def quick_fact_check(self, claim: str) -> str:
        """
        Quickly verify a specific factual claim using web search grounding.

        Args:
            claim: The specific claim to verify.
        Returns:
            Verdict with sources.
        """
        if not self._client:
            return "Not available."
        try:
            from google.genai import types as gt
            prompt = (
                f"Fact-check this claim: '{claim}'\n\n"
                "Search for current, authoritative sources. "
                "Return: VERDICT (True/False/Partially True/Unverifiable), "
                "then a 2-3 sentence explanation with sources."
            )
            response = self._client.models.generate_content(
                model=FLASH_MODEL,
                contents=prompt,
                config=gt.GenerateContentConfig(
                    tools=[gt.Tool(google_search=gt.GoogleSearch())],
                    max_output_tokens=512,
                    temperature=0.1,
                )
            )
            return response.text or "Could not verify."
        except Exception as e:
            return f"Fact-check error: {e}"

    # ── ADK tool declarations ─────────────────────────────────────────────────

    def get_adk_tools(self) -> list:
        from google.genai import types as gt
        return [
            gt.FunctionDeclaration(
                name="deep_research",
                description=(
                    "Conduct thorough multi-step web research on a topic. "
                    "Use this when the user wants comprehensive research, analysis, "
                    "or a detailed report — not just a quick lookup. "
                    "Takes 1-4 minutes but produces a detailed, cited report."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "query": gt.Schema(
                            type=gt.Type.STRING,
                            description="Detailed description of what to research"
                        ),
                        "depth": gt.Schema(
                            type=gt.Type.STRING,
                            description=(
                                "Research depth: "
                                "'quick' (~1 min, overview), "
                                "'standard' (~2-3 min, detailed), "
                                "'thorough' (~5 min, exhaustive)"
                            )
                        ),
                    },
                    required=["query"]
                )
            ),
            gt.FunctionDeclaration(
                name="fact_check",
                description=(
                    "Quickly verify whether a specific claim is true or false "
                    "using live web search. Returns verdict + sources."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "claim": gt.Schema(
                            type=gt.Type.STRING,
                            description="The specific factual claim to verify"
                        )
                    },
                    required=["claim"]
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "deep_research":
            return self.research(
                query=args.get("query", ""),
                depth=args.get("depth", "standard")
            )
        elif name == "fact_check":
            return self.quick_fact_check(args.get("claim", ""))
        return f"Unknown research tool: {name}"
