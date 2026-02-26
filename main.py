"""
ARC — Artificial Reality Companion
Entry point.
"""

import logging
import os
import sys

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("arc")

# ── Suppress noisy Qt warnings ────────────────────────────────────────────────
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()


def main():
    # Enable high-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ARC")
    app.setApplicationDisplayName("ARC — Artificial Reality Companion")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ARC")

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY not set. "
            "Agents will not function until you add your key to .env"
        )
        # Show warning but still launch (user might add it later)
        msg = QMessageBox()
        msg.setWindowTitle("ARC — API Key Missing")
        msg.setText(
            "⚠  GEMINI_API_KEY is not set.\n\n"
            "ARC will launch but Artificial Friends will not work "
            "until you add your Google Gemini API key to the .env file.\n\n"
            "See README.md for setup instructions."
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #0d1117;
                color: #e8f0fe;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QPushButton {
                background-color: #00a8d8;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 20px;
                font-family: Consolas, monospace;
                font-weight: bold;
            }
        """)
        msg.exec()

    # Launch main window
    from arc.ui.main_window import MainWindow
    window = MainWindow(api_key=api_key)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
