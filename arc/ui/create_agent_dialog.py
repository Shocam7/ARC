"""
CreateAgentDialog — Popup for configuring and spawning a new Artificial Friend (AF).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


# Gemini Live supported voices
AVAILABLE_VOICES = [
    "Aoede", "Charon", "Fenrir", "Kore", "Puck",
    "Orbit", "Zephyr", "Leda", "Orus", "Schedar",
]

PERSONA_PRESETS = {
    "— Custom —": "",
    "Research Assistant": (
        "You are a meticulous research assistant with deep expertise across all domains. "
        "You excel at finding information, synthesizing knowledge, and presenting clear summaries. "
        "You are thorough, precise, and always cite your sources."
    ),
    "Code Companion": (
        "You are an expert software engineer with deep knowledge of Python, JavaScript, "
        "system architecture, and DevOps. You write clean, production-quality code, "
        "explain complex concepts simply, and debug issues systematically."
    ),
    "Creative Partner": (
        "You are a wildly imaginative creative collaborator with expertise in writing, "
        "design thinking, and brainstorming. You push boundaries, generate unexpected ideas, "
        "and help transform vague concepts into compelling realities."
    ),
    "Productivity Coach": (
        "You are an efficiency-obsessed productivity coach who helps organize tasks, "
        "streamline workflows, manage schedules, and eliminate bottlenecks. "
        "You are direct, action-oriented, and keep focus on outcomes."
    ),
    "Data Analyst": (
        "You are a sharp data analyst who excels at interpreting numbers, spotting patterns, "
        "building visualizations, and delivering business insights. "
        "You make data accessible and actionable."
    ),
}


class CreateAgentDialog(QDialog):
    """Modal dialog for creating a new Artificial Friend."""

    agent_created = pyqtSignal(dict)  # emits agent config dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("create_af_dialog")
        self.setWindowTitle("Create Artificial Friend")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._init_ui()

    def _init_ui(self):
        # Outer container (for rounded, bordered look)
        outer = QWidget(self)
        outer.setObjectName("create_af_dialog")
        outer.setStyleSheet("""
            QWidget#create_af_dialog {
                background-color: #0d1117;
                border: 1px solid rgba(0, 200, 255, 0.3);
                border-radius: 16px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(outer)

        layout = QVBoxLayout(outer)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("+ NEW ARTIFICIAL FRIEND")
        title.setObjectName("dialog_title")
        subtitle = QLabel("CONFIGURE AGENT")
        subtitle.setObjectName("dialog_subtitle")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(subtitle)
        layout.addLayout(hdr)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(0, 200, 255, 0.15);")
        layout.addWidget(line)
        layout.addSpacing(4)

        # ── Name ─────────────────────────────────────────────
        layout.addWidget(self._field_label("AGENT NAME"))
        self.name_input = QLineEdit()
        self.name_input.setObjectName("dialog_input")
        self.name_input.setPlaceholderText("e.g. ARIA, NEXUS, VEGA...")
        layout.addWidget(self.name_input)

        # ── Persona Preset ───────────────────────────────────
        layout.addWidget(self._field_label("PERSONA PRESET"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("voice_combo")
        for key in PERSONA_PRESETS:
            self.preset_combo.addItem(key)
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        layout.addWidget(self.preset_combo)

        # ── Custom Persona ───────────────────────────────────
        layout.addWidget(self._field_label("PERSONA / SYSTEM PROMPT"))
        self.persona_input = QTextEdit()
        self.persona_input.setObjectName("persona_input")
        self.persona_input.setPlaceholderText(
            "Describe your agent's personality, expertise, and communication style..."
        )
        self.persona_input.setFixedHeight(100)
        layout.addWidget(self.persona_input)

        # ── Voice ────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(16)

        voice_col = QVBoxLayout()
        voice_col.setSpacing(6)
        voice_col.addWidget(self._field_label("VOICE"))
        self.voice_combo = QComboBox()
        self.voice_combo.setObjectName("voice_combo")
        for v in AVAILABLE_VOICES:
            self.voice_combo.addItem(v)
        voice_col.addWidget(self.voice_combo)
        row.addLayout(voice_col)

        # ── Capabilities ─────────────────────────────────────
        cap_col = QVBoxLayout()
        cap_col.setSpacing(6)
        cap_col.addWidget(self._field_label("CAPABILITIES"))
        caps_label = QLabel("Web ✓  Screen ✓  Keyboard ✓  TTS ✓")
        caps_label.setStyleSheet(
            "color: #4a5a6e; font-size: 10px; letter-spacing: 1px; "
            "background: rgba(0,200,255,0.05); border: 1px solid rgba(0,200,255,0.12); "
            "border-radius: 4px; padding: 8px 10px;"
        )
        cap_col.addWidget(caps_label)
        row.addLayout(cap_col)

        layout.addLayout(row)
        layout.addSpacing(8)

        # ── Buttons ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.reject)

        self.create_btn = QPushButton("SPAWN AGENT →")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.clicked.connect(self._on_create)
        self.create_btn.setDefault(True)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.create_btn)
        layout.addLayout(btn_row)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff3b5c; font-size: 10px; letter-spacing: 1px;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("field_label")
        return lbl

    def _apply_preset(self, preset_name: str):
        text = PERSONA_PRESETS.get(preset_name, "")
        if text:
            self.persona_input.setPlainText(text)

    def _on_create(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText("⚠  Agent name is required.")
            self.error_label.show()
            return

        persona = self.persona_input.toPlainText().strip()
        if not persona:
            persona = (
                f"You are {name}, a helpful and capable AI assistant. "
                "You are friendly, knowledgeable, and ready to assist with any task."
            )

        config = {
            "name": name,
            "persona": persona,
            "voice": self.voice_combo.currentText(),
        }
        self.agent_created.emit(config)
        self.accept()
