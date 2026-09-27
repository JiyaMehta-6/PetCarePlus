"""Centralised theme system for PetCare+.

Two purpose-built palettes (light / dark) and generated QSS so colours are
never scattered across widgets. The dark theme is designed, not simply
inverted, and maintains contrast.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    primary: str
    primary_hover: str
    secondary: str
    accent: str
    accent_hover: str
    soft: str
    text: str
    muted: str
    border: str
    warning: str
    danger: str
    success: str
    shadow: str


LIGHT = Palette(
    name="light",
    bg="#F7F5EF",
    surface="#FFFDF8",
    surface_alt="#F1ECE2",
    primary="#174A43",
    primary_hover="#1E5C53",
    secondary="#3F7770",
    accent="#E78A5B",
    accent_hover="#D97745",
    soft="#E8D9C8",
    text="#1D2926",
    muted="#71807B",
    border="#E2D9CC",
    warning="#D97745",
    danger="#B94A48",
    success="#4F8068",
    shadow="rgba(23,74,67,0.10)",
)

DARK = Palette(
    name="dark",
    bg="#111918",
    surface="#182321",
    surface_alt="#1F2C29",
    primary="#9ED1C3",
    primary_hover="#B6E0D4",
    secondary="#6FA89C",
    accent="#F0A17B",
    accent_hover="#E78A5B",
    soft="#22302D",
    text="#F3F5F2",
    muted="#9BAAA5",
    border="#263530",
    warning="#E0975F",
    danger="#E0726F",
    success="#7FB89A",
    shadow="rgba(0,0,0,0.45)",
)


def get_palette(mode: str) -> Palette:
    mode = (mode or "light").lower()
    if mode == "dark":
        return DARK
    if mode == "system":
        return _system_palette()
    return LIGHT


def _system_palette() -> Palette:
    """Follow the operating system colour scheme when the user picks 'System'."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        hints = QGuiApplication.styleHints()
        if hints is not None and hints.colorScheme() == Qt.ColorScheme.Dark:
            return DARK
    except Exception:
        pass
    return LIGHT


def build_qss(p: Palette) -> str:
    return f"""
    QWidget {{
        background-color: {p.bg};
        color: {p.text};
        font-family: 'Inter', 'Segoe UI', 'IBM Plex Sans', 'Noto Sans', sans-serif;
        font-size: 10pt;
    }}
    QMainWindow, QDialog {{
        background-color: {p.bg};
    }}
    /* Sidebar */
    #Sidebar {{
        background-color: {p.surface};
        border-right: 1px solid {p.border};
    }}
    #SidebarLabel {{
        color: {p.muted};
    }}
    /* Nav buttons */
    QPushButton[nav="true"] {{
        background-color: transparent;
        color: {p.muted};
        border: none;
        border-radius: 10px;
        padding: 9px 12px;
        text-align: left;
    }}
    QPushButton[nav="true"]:hover {{
        background-color: {p.surface_alt};
        color: {p.text};
    }}
    QPushButton[nav="true"][active="true"] {{
        background-color: {p.soft};
        color: {p.primary};
        font-weight: 600;
    }}
    /* Cards */
    #Card {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    #SurfaceCard {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    /* Primary button */
    QPushButton[primary="true"] {{
        background-color: {p.primary};
        color: {'#FFFFFF' if p.name=='light' else '#0E1614'};
        border: none;
        border-radius: 10px;
        padding: 10px 18px;
        font-weight: 600;
    }}
    QPushButton[primary="true"]:hover {{
        background-color: {p.primary_hover};
    }}
    QPushButton[primary="true"]:disabled {{
        background-color: {p.muted};
        color: {p.surface};
    }}
    /* Accent / send button */
    QPushButton[accent="true"] {{
        background-color: {p.accent};
        color: {'#FFFFFF' if p.name=='light' else '#1A1206'};
        border: none;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 700;
    }}
    QPushButton[accent="true"]:hover {{
        background-color: {p.accent_hover};
    }}
    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 10px;
        padding: 10px;
        color: {p.text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1.5px solid {p.secondary};
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.muted};
    }}
    QLabel#muted {{ color: {p.muted}; }}
    QLabel#title {{ color: {p.text}; font-weight: 700; font-size: 17pt; }}
    QLabel#subtitle {{ color: {p.muted}; font-size: 11pt; }}
    QLabel#accentLabel {{ color: {p.accent}; font-weight: 600; }}
    QLabel#primaryLabel {{ color: {p.primary}; font-weight: 700; font-size: 12pt; }}
    QLabel#dangerLabel {{ color: {p.danger}; font-weight: 700; }}
    QLabel#warningLabel {{ color: {p.warning}; font-weight: 700; }}
    QFrame#divider {{ background-color: {p.border}; max-height: 1px; }}
    """
