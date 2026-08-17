"""Centralized Qt stylesheet for AURA Desktop."""

APP_STYLE = """
QWidget {
    background: #0f1218;
    color: #e5e7eb;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}
QMainWindow, QStackedWidget {
    background: #0f1218;
}
QLabel#title {
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
}
QLabel#subtitle {
    color: #94a3b8;
}
QPushButton {
    background: #1f2937;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 12px;
}
QPushButton:hover {
    background: #273449;
}
QPushButton:checked {
    background: #2563eb;
    border-color: #3b82f6;
}
QPushButton:disabled {
    color: #64748b;
    background: #151a22;
}
QTextEdit {
    background: #151a22;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px;
    color: #f8fafc;
}
QScrollArea {
    border: none;
}
QFrame#userMessage {
    background: #1d4ed8;
    border-radius: 8px;
}
QFrame#auraMessage {
    background: #171c25;
    border: 1px solid #283244;
    border-radius: 8px;
}
QLabel#messageAuthor {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
}
QLabel#messageBody {
    color: #f8fafc;
    line-height: 145%;
}
QFrame#card {
    background: #151a22;
    border: 1px solid #283244;
    border-radius: 8px;
}
QCheckBox {
    spacing: 8px;
}
QScrollBar:vertical {
    background: #0f1218;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
}
"""
