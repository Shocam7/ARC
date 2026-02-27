"""
ARC Style System — Two distinct themes:
  LANDING:  Clean Google-style white/light design
  ROOM:     Google Meet dark (#202124) design
"""

# ── Landing palette ───────────────────────────────────────────────────────────
LANDING_STYLESHEET = """
QMainWindow, QWidget#landing_page {
    background-color: #ffffff;
}
QWidget {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    color: #202124;
    background-color: transparent;
}
QLineEdit#room_input {
    background-color: #ffffff;
    border: 1.5px solid #dadce0;
    border-radius: 8px;
    color: #202124;
    font-size: 15px;
    padding: 12px 16px;
    selection-background-color: #d2e3fc;
}
QLineEdit#room_input:focus {
    border: 1.5px solid #1a73e8;
    outline: none;
}
QPushButton#launch_btn {
    background-color: #1a73e8;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    padding: 13px 0px;
}
QPushButton#launch_btn:hover {
    background-color: #1557b0;
}
QPushButton#launch_btn:pressed {
    background-color: #0d47a1;
}
QScrollBar:vertical { background:#f8f9fa; width:6px; border-radius:3px; }
QScrollBar::handle:vertical { background:#bdc1c6; border-radius:3px; min-height:20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
"""

# ── Room / Meet palette ───────────────────────────────────────────────────────
ROOM_STYLESHEET = """
QWidget#room_view, QMainWindow {
    background-color: #202124;
}
QWidget {
    font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
    color: #e8eaed;
    background-color: transparent;
}
/* Tiles */
QWidget#meet_tile {
    background-color: #3c4043;
    border-radius: 8px;
}
QWidget#meet_tile[speaking="true"] {
    border: 2px solid #8ab4f8;
}
QLabel#tile_name_badge {
    color: #ffffff;
    font-size: 12px;
    font-weight: 500;
    background-color: rgba(0,0,0,0.6);
    border-radius: 4px;
    padding: 3px 8px;
}
/* Control bar */
QWidget#ctrl_bar {
    background-color: #202124;
    border-top: 1px solid #3c4043;
}
QPushButton#ctrl_round {
    background-color: #3c4043;
    border: none;
    border-radius: 22px;
    color: #e8eaed;
    font-size: 18px;
    min-width: 44px; max-width: 44px;
    min-height: 44px; max-height: 44px;
}
QPushButton#ctrl_round:hover {
    background-color: #5f6368;
}
QPushButton#ctrl_round[active="false"] {
    background-color: #ea4335;
    color: #ffffff;
}
QPushButton#add_af_btn {
    background-color: transparent;
    border: 1.5px solid #8ab4f8;
    border-radius: 22px;
    color: #8ab4f8;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 20px;
}
QPushButton#add_af_btn:hover {
    background-color: rgba(138,180,248,0.12);
}
QPushButton#end_btn {
    background-color: #ea4335;
    border: none;
    border-radius: 22px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 24px;
}
QPushButton#end_btn:hover {
    background-color: #c5221f;
}
/* Chat panel */
QWidget#chat_panel {
    background-color: #2d2e30;
    border-left: 1px solid #3c4043;
    border-radius: 0px;
}
QLabel#chat_title {
    color: #e8eaed;
    font-size: 14px;
    font-weight: 600;
    padding: 16px 16px 8px 16px;
}
QTextEdit#chat_view {
    background-color: transparent;
    border: none;
    color: #bdc1c6;
    font-size: 13px;
    padding: 8px;
    line-height: 1.6;
}
/* Input bar */
QWidget#input_bar {
    background-color: #2d2e30;
    border-top: 1px solid #3c4043;
}
QLineEdit#msg_input {
    background-color: #3c4043;
    border: none;
    border-radius: 24px;
    color: #e8eaed;
    font-size: 14px;
    padding: 10px 18px;
}
QLineEdit#msg_input:focus {
    background-color: #4a4d51;
}
QPushButton#send_btn {
    background-color: #8ab4f8;
    border: none;
    border-radius: 20px;
    color: #202124;
    font-size: 14px;
    font-weight: 700;
    min-width: 40px; max-width: 40px;
    min-height: 40px; max-height: 40px;
}
QPushButton#send_btn:hover { background-color: #a8c7fa; }
/* Header */
QWidget#room_header {
    background-color: #202124;
}
QLabel#room_time {
    color: #9aa0a6;
    font-size: 13px;
}
/* Scrollbar */
QScrollBar:vertical { background:#2d2e30; width:6px; border-radius:3px; }
QScrollBar::handle:vertical { background:#5f6368; border-radius:3px; min-height:20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
/* Dialog */
QDialog#create_af_dialog {
    background-color: #292a2d;
    border-radius: 12px;
}
QLabel#dlg_title {
    color: #e8eaed;
    font-size: 18px;
    font-weight: 600;
}
QLabel#dlg_field {
    color: #9aa0a6;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLineEdit#dlg_input {
    background-color: #3c4043;
    border: 1px solid #5f6368;
    border-radius: 6px;
    color: #e8eaed;
    font-size: 14px;
    padding: 10px 14px;
}
QLineEdit#dlg_input:focus { border-color: #8ab4f8; }
QTextEdit#dlg_persona {
    background-color: #3c4043;
    border: 1px solid #5f6368;
    border-radius: 6px;
    color: #e8eaed;
    font-size: 13px;
    padding: 10px 14px;
}
QTextEdit#dlg_persona:focus { border-color: #8ab4f8; }
QComboBox#dlg_combo {
    background-color: #3c4043;
    border: 1px solid #5f6368;
    border-radius: 6px;
    color: #e8eaed;
    font-size: 13px;
    padding: 8px 14px;
}
QComboBox#dlg_combo::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #3c4043;
    border: 1px solid #5f6368;
    color: #e8eaed;
    selection-background-color: rgba(138,180,248,0.2);
    outline: none;
}
QPushButton#dlg_create {
    background-color: #1a73e8;
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 11px 32px;
}
QPushButton#dlg_create:hover { background-color: #1557b0; }
QPushButton#dlg_cancel {
    background-color: transparent;
    border: 1px solid #5f6368;
    border-radius: 6px;
    color: #9aa0a6;
    font-size: 13px;
    padding: 11px 20px;
}
QPushButton#dlg_cancel:hover { background-color: rgba(255,255,255,0.05); color: #e8eaed; }
/* Orchestrator banner */
QLabel#orch_banner {
    background-color: rgba(138,180,248,0.12);
    border-radius: 16px;
    color: #8ab4f8;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 14px;
}
"""

# Combined sheet applied to main window
ARC_STYLESHEET = LANDING_STYLESHEET + ROOM_STYLESHEET