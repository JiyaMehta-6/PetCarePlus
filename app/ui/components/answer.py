"""Answer, source, evidence and safety UI components."""

from __future__ import annotations

import re
import webbrowser
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit, QToolButton,
)
from app.ui.theme import get_palette
from app.ui.components.icons import icon
from app.rag.citations import SourceCard as SourceCardData


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _rich(text: str) -> str:
    """Escape and colour [n] citation markers for display."""
    t = _esc(text)
    t = re.sub(r"\[(\d{1,2})\]", r'<span style="color:#E78A5B;font-weight:600;">[\1]</span>', t)
    t = t.replace("\n", "<br>")
    return t


class EvidenceBadge(QWidget):
    def __init__(self, level: float, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self._level = level
        self._build(level)

    def _build(self, level: float):
        p = get_palette(self._palette_name)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if level >= 0.6:
            label, col = "High", p.success
        elif level >= 0.35:
            label, col = "Moderate", p.warning
        else:
            label, col = "Low", p.danger
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {col}; font-size: 8pt;")
        txt = QLabel(f"Evidence strength: {label}")
        txt.setStyleSheet(f"color: {col}; font-size: 8pt; font-weight: 600;")
        layout.addWidget(dot)
        layout.addWidget(txt)
        layout.addStretch(1)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self._build(self._level if hasattr(self, "_level") else 0.5)


class SafetyBanner(QWidget):
    def __init__(self, level: str, title: str, detail: str, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.setObjectName("Card")
        self._build(level, title, detail)

    def _build(self, level, title, detail):
        self._level, self._title, self._detail = level, title, detail
        p = get_palette(self._palette_name)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(icon("warning", "#FFFFFF").pixmap(22, 22))
        ic.setFixedSize(24, 24)
        col = p.danger if level == "urgent" else p.warning
        self.setStyleSheet(f"background-color: {col}; border-radius: 12px; border: none;")
        ic.setStyleSheet("background: transparent;")
        layout.addWidget(ic)
        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 11pt;")
        d = QLabel(detail)
        d.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 8pt;")
        d.setWordWrap(True)
        text.addWidget(t)
        text.addWidget(d)
        layout.addLayout(text)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self._build(self._level, self._title, self._detail)


class SourceCard(QWidget):
    toggled_ = Signal(bool)

    def __init__(self, source: dict, index: int, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self.source = source
        self.index = index
        self._palette_name = palette_name
        self._open = False
        self.setObjectName("Card")
        self._build()

    def _build(self):
        p = get_palette(self._palette_name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        head = QHBoxLayout()
        num = QLabel(f"[{self.index}]")
        num.setStyleSheet(f"color: {p.accent}; font-weight: 700; font-size: 10pt;")
        title = QLabel(self.source.get("title", "Source"))
        title.setObjectName("title")
        title.setStyleSheet("font-size: 10pt; font-weight: 600;")
        title.setWordWrap(True)
        self.toggle = QToolButton()
        self.toggle.setText("▸")
        self.toggle.setStyleSheet("border: none; color: %s;" % p.muted)
        self.toggle.clicked.connect(self._on_toggle)
        head.addWidget(num)
        head.addWidget(title, 1)
        head.addWidget(self.toggle)
        layout.addLayout(head)

        org = QLabel(self.source.get("source", ""))
        org.setObjectName("muted")
        org.setStyleSheet("font-size: 8pt;")
        layout.addWidget(org)

        self._detail = QWidget()
        dl = QVBoxLayout(self._detail)
        dl.setContentsMargins(18, 6, 0, 0)
        dl.setSpacing(4)
        meta = []
        if self.source.get("authority"):
            meta.append(f"Type: {self.source['authority']}")
        if self.source.get("region"):
            meta.append(f"Region: {self.source['region']}")
        if meta:
            m = QLabel(" · ".join(meta))
            m.setObjectName("muted")
            m.setStyleSheet("font-size: 8pt;")
            dl.addWidget(m)
        ex = QLabel(self.source.get("excerpt", ""))
        ex.setWordWrap(True)
        ex.setStyleSheet(f"font-size: 8pt; color: {p.text};")
        dl.addWidget(ex)
        url = self.source.get("source_url", "")
        if url:
            link = QPushButton("Open source ↗")
            link.setFlat(True)
            link.setStyleSheet(f"color: {p.secondary}; font-size: 8pt; text-align: left;")
            link.clicked.connect(lambda: webbrowser.open(url))
            dl.addWidget(link)
        self._detail.setVisible(False)
        layout.addWidget(self._detail)

    def _on_toggle(self):
        self._open = not self._open
        self._detail.setVisible(self._open)
        self.toggle.setText("▾" if self._open else "▸")
        self.toggled_.emit(self._open)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        # rebuild for colour refresh
        for i in reversed(range(self.layout().count())):
            w = self.layout().itemAt(i).widget()
            if w:
                w.deleteLater()
        self._build()


class AnswerCard(QWidget):
    def __init__(self, answer, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.setObjectName("Card")
        self._build(answer)

    def _build(self, answer):
        p = get_palette(self._palette_name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Safety banner
        if answer.safety and answer.safety.level != "none":
            banner = SafetyBanner(
                answer.safety.level,
                answer.safety.banner_title,
                answer.safety.banner_detail,
                self._palette_name,
            )
            layout.addWidget(banner)

        # Evidence badge
        layout.addWidget(EvidenceBadge(answer.confidence, self._palette_name))

        # Retrieval status line
        status = QLabel(answer.retrieval_report)
        status.setObjectName("muted")
        status.setStyleSheet(f"font-size: 8pt; color: {p.success};")
        layout.addWidget(status)

        # Answer body
        body = QLabel()
        body.setTextFormat(Qt.RichText)
        body.setWordWrap(True)
        body.setOpenExternalLinks(False)
        body.setText(_rich(answer.answer_text))
        body.setStyleSheet(
            f"font-size: 13.5px; color: {p.text}; line-height: 150%; "
            "padding: 0; background: transparent;"
        )
        body.setMaximumWidth(900)
        layout.addWidget(body)

        # Sources
        if answer.sources:
            src_label = QLabel("Sources")
            src_label.setObjectName("primaryLabel")
            src_label.setStyleSheet("font-size: 11pt; margin-top: 4px;")
            layout.addWidget(src_label)
            for i, s in enumerate(answer.sources, 1):
                src = s.to_dict() if hasattr(s, "to_dict") else s
                layout.addWidget(SourceCard(src, i, self._palette_name))

    def set_theme(self, palette_name: str):
        # Theme switches are handled by rebuilding the card from the stored answer.
        self._palette_name = palette_name
        pass
