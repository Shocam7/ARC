"""
Orchestrator — Central routing agent for multi-AF sessions.

When only 1 AF exists: user input goes directly to that AF.
When 2+ AFs exist: the Orchestrator decides which AF should respond.

Uses Gemini Flash for fast routing decisions (not the Live model,
since this is purely a routing/decision layer).
"""

import asyncio
import logging
import json
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("arc.orchestrator")


ORCHESTRATOR_SYSTEM = """
You are the ARC Orchestrator — an invisible coordinator managing a team of AI agents called Artificial Friends (AFs).

Your ONLY job is to decide which AF should respond to the user's message.
You are never heard by the user. You operate silently in the background.

Given:
- A list of available AFs with their names and personas
- The user's message

Output ONLY a JSON object like:
{
  "selected_agent": "AGENT_NAME",
  "reason": "brief one-line reason"
}

Selection criteria:
- Match the user's request to the agent best suited by their persona/expertise
- If the message is about coding, pick the developer agent
- If the message is about research, pick the research agent
- If it's general/unclear, pick the most recently active agent
- If only one agent exists, always pick that agent
- The selected_agent MUST be one of the names in the provided list
"""


class Orchestrator(QObject):
    """
    Routes user inputs to the correct AF.
    Transparent to the user — only active when 2+ AFs are present.
    """

    routing_decision = pyqtSignal(str, str)  # (agent_name, reason)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self._agents: dict = {}  # name → ArtificialFriend
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
        """Add an AF to the pool."""
        self._agents[agent.name] = agent
        if self._last_active is None:
            self._last_active = agent.name
        logger.info(f"Orchestrator: registered AF [{agent.name}] (total: {len(self._agents)})")

    def unregister_agent(self, name: str):
        """Remove an AF from the pool."""
        if name in self._agents:
            del self._agents[name]
        if self._last_active == name:
            self._last_active = next(iter(self._agents), None)

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    # ── Routing ────────────────────────────────────────────────────────────────

    def route(self, user_message: str) -> Optional[str]:
        """
        Decide which AF should respond.
        Returns the agent name synchronously (blocks briefly for Flash call).
        """
        if not self._agents:
            return None

        # Only 1 agent — no routing needed
        if len(self._agents) == 1:
            name = next(iter(self._agents))
            self._last_active = name
            return name

        # Multiple agents — use Flash to route
        selected = self._route_with_llm(user_message)
        if selected and selected in self._agents:
            self._last_active = selected
            return selected

        # Fallback to last active
        return self._last_active

    def _route_with_llm(self, user_message: str) -> Optional[str]:
        """Use Gemini Flash to choose the best agent."""
        if not self._client:
            return self._last_active

        # Build agent roster for the prompt
        roster = "\n".join(
            f"- {name}: {agent.persona[:150]}"
            for name, agent in self._agents.items()
        )

        prompt = f"""
Available Agents:
{roster}

User's message: "{user_message}"

Last active agent: {self._last_active or 'none'}

Which agent should respond? Return ONLY the JSON object.
""".strip()

        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "system_instruction": ORCHESTRATOR_SYSTEM,
                    "temperature": 0.1,
                    "max_output_tokens": 100,
                }
            )
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            selected = data.get("selected_agent", "")
            reason = data.get("reason", "")
            logger.info(f"Orchestrator routed to [{selected}]: {reason}")
            self.routing_decision.emit(selected, reason)
            return selected
        except json.JSONDecodeError:
            logger.warning("Orchestrator: invalid JSON from Flash, using last active")
            return self._last_active
        except Exception as e:
            logger.warning(f"Orchestrator routing failed: {e}, using last active")
            return self._last_active

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def dispatch_text(self, user_message: str) -> Optional[str]:
        """
        Route the message and send it to the selected agent.
        Returns the name of the agent that received it.
        """
        target_name = self.route(user_message)
        if target_name and target_name in self._agents:
            agent = self._agents[target_name]
            agent.send_text(user_message)
            return target_name
        return None

    def dispatch_audio(self, pcm_bytes: bytes):
        """
        Send microphone audio to the currently active agent.
        (Audio routing always goes to last active — switching happens via text routing.)
        """
        if self._last_active and self._last_active in self._agents:
            self._agents[self._last_active].send_audio(pcm_bytes)

    def get_agent(self, name: str):
        """Get an AF by name."""
        return self._agents.get(name)

    def all_agents(self) -> list:
        """Return all registered AFs."""
        return list(self._agents.values())
