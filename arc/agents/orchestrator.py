"""
Orchestrator — Central routing agent for multi-AF sessions.

Single AF:  user input → that AF directly.
2+ AFs:     Orchestrator (gemini-2.5-flash) decides which AF responds.
            Only one AF speaks at a time.
"""

import json
import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from arc.core.models import ORCHESTRATOR_MODEL

logger = logging.getLogger("arc.orchestrator")


ORCHESTRATOR_SYSTEM = """
You are the ARC Orchestrator — a silent coordinator managing a team of AI agents called Artificial Friends (AFs).

Your ONLY job: decide which AF should respond to the user's message.
You are never heard by the user. You operate silently in the background.

Given:
- A list of AFs with names and persona summaries
- The user's message
- The last-active AF

Output ONLY a JSON object:
{
  "selected_agent": "EXACT_AGENT_NAME",
  "reason": "one-line reason"
}

Rules:
- Match request to the agent whose persona best fits the task
- The selected_agent value MUST exactly match one of the provided names
- If the request is general or ambiguous, prefer the last-active agent
- If only one agent exists, always pick that agent
"""


class Orchestrator(QObject):
    """Routes user messages to the best-fit AF using gemini-2.5-flash."""

    routing_decision = pyqtSignal(str, str)   # (agent_name, reason)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key      = api_key
        self._agents: dict = {}
        self._last_active: Optional[str] = None
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Orchestrator client init failed: {e}")

    # ── Agent registry ────────────────────────────────────────────────────────

    def register_agent(self, agent):
        self._agents[agent.name] = agent
        if self._last_active is None:
            self._last_active = agent.name
        logger.info(f"Orchestrator: registered [{agent.name}] (total={len(self._agents)})")

    def unregister_agent(self, name: str):
        self._agents.pop(name, None)
        if self._last_active == name:
            self._last_active = next(iter(self._agents), None)

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    # ── Routing ───────────────────────────────────────────────────────────────

    def route(self, user_message: str) -> Optional[str]:
        """Return the name of the AF that should respond. Blocks briefly."""
        if not self._agents:
            return None
        if len(self._agents) == 1:
            name = next(iter(self._agents))
            self._last_active = name
            return name
        selected = self._route_with_llm(user_message)
        if selected and selected in self._agents:
            self._last_active = selected
            return selected
        return self._last_active

    def _route_with_llm(self, user_message: str) -> Optional[str]:
        """Call gemini-2.5-flash to pick the best agent (~150-250ms)."""
        if not self._client:
            return self._last_active

        roster = "\n".join(
            f"- {name}: {agent.persona[:180]}"
            for name, agent in self._agents.items()
        )
        prompt = (
            f"Agents:\n{roster}\n\n"
            f'User message: "{user_message}"\n'
            f"Last active: {self._last_active or 'none'}\n\n"
            "Which agent should respond? Return ONLY the JSON."
        )

        try:
            from google.genai import types as gt
            response = self._client.models.generate_content(
                model=ORCHESTRATOR_MODEL,
                contents=prompt,
                config=gt.GenerateContentConfig(
                    system_instruction=ORCHESTRATOR_SYSTEM,
                    temperature=0.1,
                    max_output_tokens=120,
                )
            )
            text = response.text.strip()
            # Strip markdown fences
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            selected = data.get("selected_agent", "")
            reason   = data.get("reason", "")
            logger.info(f"Orchestrator → [{selected}]: {reason}")
            self.routing_decision.emit(selected, reason)
            return selected
        except json.JSONDecodeError:
            logger.warning("Orchestrator: bad JSON from model, falling back")
            return self._last_active
        except Exception as e:
            logger.warning(f"Orchestrator routing error: {e}")
            return self._last_active

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def dispatch_text(self, user_message: str) -> Optional[str]:
        """Route and deliver a text message. Returns receiving agent name."""
        target = self.route(user_message)
        if target and target in self._agents:
            self._agents[target].send_text(user_message)
            return target
        return None

    def dispatch_audio(self, pcm_bytes: bytes):
        """Send mic audio to the currently active agent."""
        if self._last_active and self._last_active in self._agents:
            self._agents[self._last_active].send_audio(pcm_bytes)

    def get_agent(self, name: str):
        return self._agents.get(name)

    def all_agents(self) -> list:
        return list(self._agents.values())
