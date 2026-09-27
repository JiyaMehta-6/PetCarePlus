"""Loading, empty and status states."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from app.ui.theme import get_palette
from app.ui.components.illustrations import KnowledgePulse


class LoadingState(QWidget):
    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)
        self.pulse = KnowledgePulse()
        self.pulse.set_theme(self._palette_name)
        layout.addWidget(self.pulse, alignment=Qt.AlignCenter)
        self.label = QLabel("Working…")
        self.label.setObjectName("muted")
        self.label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.label, alignment=Qt.AlignCenter)

    def set_stage(self, text: str):
        self.label.setText(text)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self.pulse.set_theme(palette_name)


class EmptyState(QWidget):
    def __init__(self, title: str, subtitle: str, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        t = QLabel(title)
        t.setObjectName("title")
        t.setStyleSheet("font-size: 14pt;")
        t.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        t.setWordWrap(True)
        s = QLabel(subtitle)
        s.setObjectName("subtitle")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        s.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout.addWidget(t, alignment=Qt.AlignCenter)
        layout.addWidget(s, alignment=Qt.AlignCenter)
        self._title = t
        self._subtitle = s

    def _fit(self):
        # QLabel with wordWrap does not always report a height that fits its
        # wrapped text, which clips the bottom lines inside scroll areas. Force
        # each label's minimum height to match what its current width needs.
        for lbl in (self._title, self._subtitle):
            if lbl.wordWrap() and lbl.width() > 0:
                h = lbl.heightForWidth(lbl.width())
                if h > 0:
                    lbl.setMinimumHeight(h)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._fit()


class RetrievalStatus(QWidget):
    """Subtle status such as '✓ 6 relevant sources found'."""

    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self._build()

    def _build(self):
        self.label = QLabel("")
        self.label.setObjectName("muted")
        p = get_palette(self._palette_name)
        self.label.setStyleSheet(f"font-size: 8pt; color: {p.success};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

    def set_text(self, text: str):
        self.label.setText(text)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        p = get_palette(palette_name)
        self.label.setStyleSheet(f"font-size: 8pt; color: {p.success};")
