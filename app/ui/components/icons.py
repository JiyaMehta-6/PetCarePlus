"""Vector icon factory for PetCare+.

Icons are drawn as inline SVG (no external assets, no internet) and rendered to
QIcon. Avoids emoji inconsistencies across OSes.
"""

from __future__ import annotations

import os

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "logo.svg"
)


def _svg_icon(svg: str, size: int = 24) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return QIcon(pm)


# Stroke-based 24x24 icons (currentColor via stroke="#xxxxxx" set by caller).
_STROKE = '#174A43'

_ICONS = {
    "search": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "pets": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="9" r="1.6"/><circle cx="10" cy="6" r="1.6"/><circle cx="14" cy="6" r="1.6"/><circle cx="18" cy="9" r="1.6"/><path d="M12 12c-3 0-5 2-5 4.5C7 19 9 21 12 21s5-2 5-4.5c0-2.5-2-4.5-5-4.5z"/></svg>',
    "sources": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v14H4z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="8" y1="13" x2="16" y2="13"/></svg>',
    "history": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><polyline points="12 8 12 12 15 14"/></svg>',
    "settings": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L13.5 2h-3l-.5 2.5a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2L9.5 22h3l.5-2.5a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"/></svg>',
    "warning": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20L12 3z"/><line x1="12" y1="9" x2="12" y2="14"/><circle cx="12" cy="17" r="0.6" fill="{_STROKE}"/></svg>',
    "delete": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 20 7"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/></svg>',
    "back": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="15" y1="5" x2="8" y2="12"/><polyline points="15 5 8 12 15 19"/></svg>',
    "close": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>',
    "plus": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "send": f'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    "home": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
    "book": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h6v16H6a2 2 0 0 0-2 2z"/><path d="M20 5a2 2 0 0 0-2-2h-6v16h6a2 2 0 0 1 2 2z"/></svg>',
    "shield": f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{_STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6l8-3z"/></svg>',
}


def icon(name: str, color: str | None = None, size: int = 24) -> QIcon:
    svg = _ICONS.get(name, _ICONS["search"])
    if color and color != _STROKE:
        svg = svg.replace(_STROKE, color)
    return _svg_icon(svg, size)


def logo_pixmap(size: int = 64) -> QPixmap:
    """Render the PetCare+ logo SVG (assets/logo.svg) at the given size."""
    renderer = QSvgRenderer(_LOGO_PATH)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


def logo_icon(size: int = 64) -> QIcon:
    return QIcon(logo_pixmap(size))
