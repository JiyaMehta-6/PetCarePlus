"""Custom vector illustrations drawn with QPainter (no external assets).

Provides a calm, premium visual identity: a knowledge pulse, a care
constellation and an abstract species mark used on the home screen and empty
states.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPainterPath
from PySide6.QtWidgets import QWidget

from app.ui.theme import get_palette


class KnowledgePulse(QWidget):
    """A soft animated 'pulse' of concentric arcs suggesting retrieval."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self._t = 0.0

    def set_theme(self, palette_name: str):
        self._p = get_palette(palette_name)
        self.update()

    def paintEvent(self, ev):
        p = getattr(self, "_p", get_palette("light"))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        core = QColor(p.primary)
        glow = QRadialGradient(cx, cy, self.width() / 2)
        glow.setColorAt(0, QColor(p.primary if p.name == "light" else p.primary))
        glow.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(0, 0, self.width(), self.height()))
        # concentric arcs
        for i in range(3):
            r = 18 + i * 16
            alpha = 200 - i * 55
            pen = QPen(QColor(p.secondary))
            pen.setWidth(2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setColor(QColor(p.secondary))
            col = QColor(p.secondary)
            col.setAlpha(alpha)
            pen.setColor(col)
            painter.setPen(pen)
            span = 300 - i * 40
            painter.drawArc(int(cx - r), int(cy - r), r * 2, r * 2, int((self._t * 360 + i * 40) * 16), int(span * 16))
        painter.setBrush(QColor(p.primary))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - 9, cy - 9, 18, 18))
        painter.end()


class CareConstellation(QWidget):
    """Abstract 'care constellation' - connected nodes representing species."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 150)
        self._nodes = [
            (0.20, 0.30), (0.40, 0.18), (0.62, 0.32), (0.80, 0.22),
            (0.30, 0.62), (0.55, 0.66), (0.74, 0.60), (0.50, 0.42),
        ]

    def set_theme(self, palette_name: str):
        self._p = get_palette(palette_name)
        self.update()

    def paintEvent(self, ev):
        p = getattr(self, "_p", get_palette("light"))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pts = [QPointF(x * w, y * h) for x, y in self._nodes]
        pen = QPen(QColor(p.soft))
        pen.setWidth(1.5)
        painter.setPen(pen)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if (i + j) % 2 == 0:
                    painter.drawLine(pts[i], pts[j])
        for i, pt in enumerate(pts):
            col = QColor(p.secondary if i % 2 else p.accent)
            painter.setBrush(col)
            painter.setPen(Qt.PenStyle.NoPen)
            r = 6 if i % 2 else 8
            painter.drawEllipse(QRectF(pt.x() - r, pt.y() - r, r * 2, r * 2))
        painter.end()


class SpeciesMark(QWidget):
    """Abstract rounded species silhouette for pet profile cards."""

    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self._p = get_palette(palette_name)

    def set_theme(self, palette_name: str):
        self._p = get_palette(palette_name)
        self.update()

    def paintEvent(self, ev):
        p = self._p
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(p.soft))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 54, 54, 16, 16)
        painter.setBrush(QColor(p.secondary))
        # simple abstract head + ears
        painter.drawEllipse(17, 20, 20, 18)
        painter.drawEllipse(15, 14, 7, 9)
        painter.drawEllipse(32, 14, 7, 9)
        painter.setBrush(QColor(p.bg))
        painter.drawEllipse(23, 26, 3, 3)
        painter.drawEllipse(31, 26, 3, 3)
        painter.end()
