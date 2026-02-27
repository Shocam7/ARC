"""
DeepResearchCapability — Multi-step autonomous web research via Vertex AI.

Uses gemini-2.5-flash with Google Search grounding on Vertex AI.
Authentication: ADC — no api_key.

When the dedicated deep-research model becomes generally available on Vertex AI,
update DEEP_RESEARCH_MODEL in arc/core/models.py to point to it.
"""

import logging
import time

logger = logging.getLogger("arc.capabilities.deep_research")

from arc.core.models import DEEP_RESEARCH_MODEL, FLASH_MODEL
from arc.core.vertex_config import make_standard_client


class DeepResearchCapability:
    """
    Performs thorough multi-step research using gemini-2.5-flash on Vertex AI
    with Google Search grounding enabled.
    No api_key — uses Application Default Credentials.
    """

    def __init__(self):
        self._client = None
        try:
            self._client = make_standard_client()
        except Exception as e:
            logger.error(f"DeepResearch client init: {e}")

    def research(self, query: str, depth: str = "standard") -> str:
        """
        Conduct deep multi-step web research on a topic via Vertex AI.

        Args:
            query: What to research. Be specific.
            depth: 'quick' (fast), 'standard' (thorough), 'thorough' (comprehensive).
        Returns:
            A structured research report with sources.
        """
        if not self._client:
            return "Deep Research not available (Vertex AI not configured)."

        logger.info(f"DeepResearch: researching: {query[:80]}")
        start = time.time()

        depth_tokens = {
            "quick":    {"max_output": 1024},
            "standard": {"max_output": 3072},
            "thorough": {"max_output": 6144},
        }
        cfg = depth_tokens.get(depth, depth_tokens["standard"])

        prompt = (
            f"Research the following topic thoroughly:\n\n{query}\n\n"
            "Provide a structured report with:\n"
            "1. Executive Summary (2-3 sentences)\n"
            "2. Key Findings (bullet points)\n"
            "3. Detailed Analysis\n"
            "4. Sources and Citations\n"
            "5. Confidence level for key claims\n\n"
            "Use web search to find current, accurate information. "
            "Cite all sources."
        )

        try:
            from google.genai import types as gt

            # Enable Google Search grounding for up-to-date web data
            tools = [gt.Tool(google_search=gt.GoogleSearch())]

            resp = self._client.models.generate_content(
                model=DEEP_RESEARCH_MODEL,
                contents=prompt,
                config=gt.GenerateContentConfig(
                    tools=tools,
                    temperature=0.2,
                    max_output_tokens=cfg["max_output"],
                ),
            )
            elapsed = time.time() - start
            result  = resp.text or "No research results returned."
            logger.info(f"DeepResearch completed in {elapsed:.1f}s")

            # Append grounding citations if available
            if (hasattr(resp, "candidates") and resp.candidates and
                    hasattr(resp.candidates[0], "grounding_metadata") and
                    resp.candidates[0].grounding_metadata):
                gm = resp.candidates[0].grounding_metadata
                if hasattr(gm, "web_search_queries"):
                    result += f"\n\n[Searches: {', '.join(gm.web_search_queries)}]"

            return result

        except Exception as e:
            logger.error(f"DeepResearch failed: {e}")
            # Fallback: plain Flash without grounding
            try:
                resp = self._client.models.generate_content(
                    model=FLASH_MODEL,
                    contents=prompt,
                    config={"temperature": 0.2,
                            "max_output_tokens": cfg["max_output"]},
                )
                return resp.text or "No results."
            except Exception as e2:
                return f"Research error: {e2}"

    def fact_check(self, claim: str) -> str:
        """
        Verify a specific claim using web search grounding on Vertex AI.

        Args:
            claim: The claim to verify.
        Returns:
            Verdict with supporting evidence and sources.
        """
        if not self._client:
            return "Fact check not available (Vertex AI not configured)."

        prompt = (
            f"Fact-check this claim: \"{claim}\"\n\n"
            "Using web search, determine if this claim is:\n"
            "- TRUE: well-supported by reliable sources\n"
            "- FALSE: contradicted by reliable sources\n"
            "- PARTIALLY TRUE: some aspects correct, some incorrect\n"
            "- UNVERIFIABLE: insufficient evidence found\n\n"
            "Provide: verdict, evidence summary, key sources."
        )

        try:
            from google.genai import types as gt
            tools = [gt.Tool(google_search=gt.GoogleSearch())]
            resp  = self._client.models.generate_content(
                model=FLASH_MODEL,
                contents=prompt,
                config=gt.GenerateContentConfig(
                    tools=tools,
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            return resp.text or "Fact check returned no result."
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return f"Fact check error: {e}"

    def get_adk_tools(self) -> list:
        from google.genai import types as gt
        return [
            gt.FunctionDeclaration(
                name="deep_research",
                description=(
                    "Conduct thorough multi-step web research on a topic using "
                    "Vertex AI with Google Search grounding. Use for comprehensive "
                    "research that requires synthesising multiple sources."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "query": gt.Schema(type=gt.Type.STRING,
                                           description="The research question or topic"),
                        "depth": gt.Schema(type=gt.Type.STRING,
                                           description="'quick'|'standard'|'thorough'"),
                    },
                    required=["query"],
                ),
            ),
            gt.FunctionDeclaration(
                name="fact_check",
                description=(
                    "Verify a specific claim using live web search on Vertex AI. "
                    "Returns verdict (TRUE/FALSE/PARTIALLY TRUE/UNVERIFIABLE) with evidence."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "claim": gt.Schema(type=gt.Type.STRING,
                                           description="The claim to verify"),
                    },
                    required=["claim"],
                ),
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "deep_research":
            return self.research(
                args.get("query", ""),
                args.get("depth", "standard"),
            )
        elif name == "fact_check":
            return self.fact_check(args.get("claim", ""))
        return f"Unknown research tool: {name}"