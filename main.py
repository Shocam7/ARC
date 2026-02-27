"""
ARC — Artificial Reality Companion
Entry point.

Authentication: Vertex AI Application Default Credentials (ADC)

Setup before running:
  1. Install Google Cloud CLI:   https://cloud.google.com/sdk/docs/install
  2. Authenticate:               gcloud auth application-default login
  3. Set env vars in .env:
       GOOGLE_CLOUD_PROJECT=your-gcp-project-id
       GOOGLE_CLOUD_LOCATION=us-central1
  4. Enable Vertex AI API in your project:
       gcloud services enable aiplatform.googleapis.com
  5. Run:                        python main.py
"""

import logging
import os
import sys

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("arc")

os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()


def _check_vertex_config() -> tuple[bool, str]:
    """Validate Vertex AI environment configuration before launching."""
    from arc.core.vertex_config import validate_config
    return validate_config()


def _show_config_warning(message: str):
    """Show a friendly warning dialog with setup instructions."""
    msg = QMessageBox()
    msg.setWindowTitle("ARC — Vertex AI Setup Required")
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setText(
        "⚠  Vertex AI is not configured.\n\n"
        + message +
        "\n\nSee README.md → Vertex AI Setup for full instructions.\n"
        "ARC will launch but agents won't work until this is resolved."
    )
    msg.setDetailedText(
        "Quick setup steps:\n"
        "1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install\n"
        "2. Run: gcloud auth application-default login\n"
        "3. Add to .env:\n"
        "     GOOGLE_CLOUD_PROJECT=your-project-id\n"
        "     GOOGLE_CLOUD_LOCATION=us-central1\n"
        "4. Enable API: gcloud services enable aiplatform.googleapis.com\n"
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.setStyleSheet("""
        QMessageBox {
            background-color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        QPushButton {
            background-color: #1a73e8;
            border: none;
            border-radius: 6px;
            color: white;
            padding: 8px 24px;
            font-weight: 600;
        }
        QPushButton:hover { background-color: #1557b0; }
    """)
    msg.exec()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ARC")
    app.setApplicationDisplayName("ARC — Artificial Reality Companion")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("ARC")

    # Validate Vertex AI config
    ok, msg = _check_vertex_config()
    if not ok:
        logger.warning(f"Vertex AI config issue: {msg}")
        _show_config_warning(msg)
    else:
        logger.info(msg)

    # Launch main window (no api_key — Vertex AI ADC handles auth)
    from arc.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()