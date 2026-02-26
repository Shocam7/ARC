"""
ARC Design System — Retrofuturistic Dark Theme
Palette: Deep Space Black + Electric Cyan + Neon Amber
"""

COLORS = {
    "bg_deep":        "#07090f",
    "bg_panel":       "#0d1117",
    "bg_elevated":    "#131926",
    "bg_glass":       "rgba(255, 255, 255, 0.04)",
    "border":         "rgba(0, 200, 255, 0.18)",
    "border_hover":   "rgba(0, 200, 255, 0.45)",
    "border_active":  "#00c8ff",
    "accent_cyan":    "#00c8ff",
    "accent_amber":   "#ff9500",
    "accent_red":     "#ff3b5c",
    "accent_green":   "#00e676",
    "text_primary":   "#e8f0fe",
    "text_secondary": "#8ba0b8",
    "text_muted":     "#4a5a6e",
    "speaking_glow":  "rgba(0, 200, 255, 0.35)",
    "tile_bg":        "#0f1520",
}

ARC_STYLESHEET = """
/* ─── Root ─────────────────────────────────────────────── */
* {
    font-family: 'Consolas', 'Courier New', monospace;
    outline: none;
}

QMainWindow {
    background-color: #07090f;
}

QWidget {
    background-color: transparent;
    color: #e8f0fe;
}

/* ─── Scrollbar ─────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0d1117;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(0, 200, 255, 0.3);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ─── Main Background Widget ────────────────────────────── */
QWidget#root_bg {
    background-color: #07090f;
}

/* ─── Landing Page ──────────────────────────────────────── */
QWidget#landing_page {
    background-color: #07090f;
}

QLabel#arc_logo {
    color: #00c8ff;
    font-size: 62px;
    font-weight: 900;
    letter-spacing: 14px;
    font-family: 'Consolas', monospace;
}

QLabel#arc_tagline {
    color: #4a5a6e;
    font-size: 11px;
    letter-spacing: 5px;
    font-family: 'Consolas', monospace;
}

QLabel#landing_desc {
    color: #8ba0b8;
    font-size: 13px;
    letter-spacing: 1px;
}

QLineEdit#room_input {
    background-color: rgba(0, 200, 255, 0.05);
    border: 1px solid rgba(0, 200, 255, 0.22);
    border-radius: 6px;
    color: #e8f0fe;
    font-size: 14px;
    padding: 12px 18px;
    letter-spacing: 2px;
    selection-background-color: rgba(0, 200, 255, 0.3);
}
QLineEdit#room_input:focus {
    border: 1px solid rgba(0, 200, 255, 0.6);
    background-color: rgba(0, 200, 255, 0.08);
}
QLineEdit#room_input::placeholder {
    color: #4a5a6e;
}

QPushButton#launch_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00a8d8, stop:1 #007aaa);
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 4px;
    padding: 14px 48px;
}
QPushButton#launch_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d4ff, stop:1 #0099cc);
}
QPushButton#launch_btn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0077aa, stop:1 #005588);
}

/* ─── Room View ─────────────────────────────────────────── */
QWidget#room_view {
    background-color: #07090f;
}

QLabel#room_title {
    color: #00c8ff;
    font-size: 12px;
    letter-spacing: 5px;
    font-weight: 600;
}

QLabel#room_id_label {
    color: #4a5a6e;
    font-size: 10px;
    letter-spacing: 3px;
}

QWidget#tiles_container {
    background-color: transparent;
}

/* ─── Video Tile ─────────────────────────────────────────── */
QWidget#agent_tile {
    background-color: #0f1520;
    border: 1px solid rgba(0, 200, 255, 0.15);
    border-radius: 12px;
}
QWidget#agent_tile[speaking="true"] {
    border: 1px solid rgba(0, 200, 255, 0.8);
}

QWidget#user_tile {
    background-color: #0f1520;
    border: 1px solid rgba(255, 149, 0, 0.25);
    border-radius: 12px;
}

QLabel#tile_name {
    color: #e8f0fe;
    font-size: 11px;
    letter-spacing: 2px;
    font-weight: 600;
    background-color: rgba(7, 9, 15, 0.85);
    padding: 4px 10px;
    border-radius: 4px;
}

QLabel#tile_status {
    color: #4a5a6e;
    font-size: 9px;
    letter-spacing: 2px;
    background-color: rgba(7, 9, 15, 0.85);
    padding: 2px 8px;
    border-radius: 3px;
}

QLabel#tile_status[state="speaking"] {
    color: #00c8ff;
}

QLabel#tile_status[state="thinking"] {
    color: #ff9500;
}

QLabel#tile_status[state="acting"] {
    color: #00e676;
}

/* ─── Avatar Widget ─────────────────────────────────────── */
QLabel#avatar_label {
    border-radius: 8px;
    background-color: #131926;
}

/* ─── Control Bar ────────────────────────────────────────── */
QWidget#control_bar {
    background-color: rgba(13, 17, 23, 0.95);
    border-top: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 0px;
}

QPushButton#add_af_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(0, 200, 255, 0.15), stop:1 rgba(0, 200, 255, 0.08));
    border: 1px solid rgba(0, 200, 255, 0.4);
    border-radius: 22px;
    color: #00c8ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    padding: 10px 28px;
    min-width: 180px;
}
QPushButton#add_af_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(0, 200, 255, 0.28), stop:1 rgba(0, 200, 255, 0.15));
    border: 1px solid #00c8ff;
}
QPushButton#add_af_btn:pressed {
    background: rgba(0, 200, 255, 0.08);
}

QPushButton#ctrl_btn {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 22px;
    color: #8ba0b8;
    font-size: 16px;
    padding: 10px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
}
QPushButton#ctrl_btn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #e8f0fe;
}

QPushButton#end_btn {
    background-color: rgba(255, 59, 92, 0.15);
    border: 1px solid rgba(255, 59, 92, 0.4);
    border-radius: 22px;
    color: #ff3b5c;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px 24px;
}
QPushButton#end_btn:hover {
    background-color: rgba(255, 59, 92, 0.3);
    border: 1px solid #ff3b5c;
}

/* ─── Create AF Dialog ──────────────────────────────────── */
QDialog#create_af_dialog {
    background-color: #0d1117;
    border: 1px solid rgba(0, 200, 255, 0.25);
    border-radius: 16px;
}

QLabel#dialog_title {
    color: #00c8ff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 5px;
}

QLabel#dialog_subtitle {
    color: #4a5a6e;
    font-size: 10px;
    letter-spacing: 3px;
}

QLabel#field_label {
    color: #8ba0b8;
    font-size: 10px;
    letter-spacing: 3px;
    font-weight: 600;
}

QLineEdit#dialog_input {
    background-color: rgba(0, 200, 255, 0.04);
    border: 1px solid rgba(0, 200, 255, 0.2);
    border-radius: 6px;
    color: #e8f0fe;
    font-size: 13px;
    padding: 10px 14px;
    letter-spacing: 1px;
}
QLineEdit#dialog_input:focus {
    border: 1px solid rgba(0, 200, 255, 0.6);
    background-color: rgba(0, 200, 255, 0.07);
}

QTextEdit#persona_input {
    background-color: rgba(0, 200, 255, 0.04);
    border: 1px solid rgba(0, 200, 255, 0.2);
    border-radius: 6px;
    color: #e8f0fe;
    font-size: 12px;
    padding: 10px 14px;
    line-height: 1.6;
}
QTextEdit#persona_input:focus {
    border: 1px solid rgba(0, 200, 255, 0.6);
    background-color: rgba(0, 200, 255, 0.07);
}

QComboBox#voice_combo {
    background-color: rgba(0, 200, 255, 0.04);
    border: 1px solid rgba(0, 200, 255, 0.2);
    border-radius: 6px;
    color: #e8f0fe;
    font-size: 12px;
    padding: 8px 14px;
}
QComboBox#voice_combo:hover {
    border: 1px solid rgba(0, 200, 255, 0.5);
}
QComboBox#voice_combo::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #131926;
    border: 1px solid rgba(0, 200, 255, 0.3);
    color: #e8f0fe;
    selection-background-color: rgba(0, 200, 255, 0.15);
    outline: none;
}

QPushButton#create_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00a8d8, stop:1 #007aaa);
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 4px;
    padding: 12px 36px;
}
QPushButton#create_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d4ff, stop:1 #0099cc);
}

QPushButton#cancel_btn {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #8ba0b8;
    font-size: 11px;
    letter-spacing: 2px;
    padding: 12px 24px;
}
QPushButton#cancel_btn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #e8f0fe;
}

/* ─── Input Bar ─────────────────────────────────────────── */
QWidget#input_bar {
    background-color: rgba(13, 17, 23, 0.9);
    border-top: 1px solid rgba(0, 200, 255, 0.08);
}

QLineEdit#text_input {
    background-color: rgba(0, 200, 255, 0.05);
    border: 1px solid rgba(0, 200, 255, 0.2);
    border-radius: 20px;
    color: #e8f0fe;
    font-size: 13px;
    padding: 10px 20px;
    letter-spacing: 0.5px;
}
QLineEdit#text_input:focus {
    border: 1px solid rgba(0, 200, 255, 0.55);
    background-color: rgba(0, 200, 255, 0.08);
}

QPushButton#send_btn {
    background: rgba(0, 200, 255, 0.15);
    border: 1px solid rgba(0, 200, 255, 0.4);
    border-radius: 20px;
    color: #00c8ff;
    font-size: 14px;
    padding: 10px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}
QPushButton#send_btn:hover {
    background: rgba(0, 200, 255, 0.28);
}

QPushButton#mic_btn {
    background-color: rgba(255, 149, 0, 0.12);
    border: 1px solid rgba(255, 149, 0, 0.35);
    border-radius: 20px;
    color: #ff9500;
    font-size: 14px;
    padding: 10px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}
QPushButton#mic_btn:hover {
    background-color: rgba(255, 149, 0, 0.25);
}
QPushButton#mic_btn[active="true"] {
    background-color: rgba(255, 149, 0, 0.35);
    border: 1px solid #ff9500;
    color: #ffffff;
}

/* ─── Toast / Notification ──────────────────────────────── */
QLabel#toast_label {
    background-color: rgba(0, 200, 255, 0.12);
    border: 1px solid rgba(0, 200, 255, 0.4);
    border-radius: 20px;
    color: #00c8ff;
    font-size: 11px;
    letter-spacing: 2px;
    padding: 8px 18px;
}

/* ─── Transcript Panel ──────────────────────────────────── */
QWidget#transcript_panel {
    background-color: rgba(13, 17, 23, 0.97);
    border-left: 1px solid rgba(0, 200, 255, 0.12);
}

QTextEdit#transcript_view {
    background-color: transparent;
    border: none;
    color: #8ba0b8;
    font-size: 12px;
    line-height: 1.8;
    padding: 12px;
}

QLabel#transcript_title {
    color: #4a5a6e;
    font-size: 10px;
    letter-spacing: 5px;
    font-weight: 600;
    padding: 12px 16px 8px 16px;
    border-bottom: 1px solid rgba(0, 200, 255, 0.08);
}

/* ─── Header Bar ─────────────────────────────────────────── */
QWidget#header_bar {
    background-color: rgba(13, 17, 23, 0.95);
    border-bottom: 1px solid rgba(0, 200, 255, 0.1);
    min-height: 52px;
    max-height: 52px;
}

QLabel#header_arc {
    color: #00c8ff;
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 8px;
}

QLabel#header_dot {
    color: #ff9500;
    font-size: 20px;
}

QLabel#connection_status {
    color: #00e676;
    font-size: 9px;
    letter-spacing: 3px;
}

/* ─── Orchestrator Badge ────────────────────────────────── */
QLabel#orch_badge {
    background-color: rgba(255, 149, 0, 0.12);
    border: 1px solid rgba(255, 149, 0, 0.4);
    border-radius: 4px;
    color: #ff9500;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 2px 8px;
}
"""
