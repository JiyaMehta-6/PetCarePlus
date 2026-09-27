"""Query input and suggestion chips."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtGui import QKeySequence, QShortcut
from app.ui.theme import get_palette
from app.ui.components.icons import icon


class SuggestionChip(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setProperty("nav", False)
        self.setObjectName("Chip")
        self.setStyleSheet(
            "SuggestionChip { border: 1px solid; border-radius: 16px; padding: 6px 14px;"
            " font-size: 9pt; }"
        )
        self.setCursor(Qt.PointingHandCursor)


class QueryInput(QWidget):
    submitted = Signal(str)

    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.box = QTextEdit()
        self.box.setPlaceholderText("What would you like to know about your pet?")
        self.box.setFixedHeight(64)
        self.box.setAcceptRichText(False)
        layout.addWidget(self.box)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.chips_label = QLabel("Try:")
        self.chips_label.setObjectName("muted")
        self.chips_label.setStyleSheet("font-size: 8pt;")
        row.addWidget(self.chips_label)

        self.chips = {}
        for label, q in [
            ("Nutrition", "What should I feed my pet?"),
            ("Toxic foods", "What foods are toxic to my pet?"),
            ("Symptoms", "My pet is not eating, what could be wrong?"),
            ("Grooming", "How do I groom my pet?"),
            ("Exercise", "How much exercise does my pet need?"),
            ("Vaccines", "What vaccinations does my pet need?"),
        ]:
            chip = SuggestionChip(label)
            chip.clicked.connect(lambda _, qq=q: self._fill(qq))
            self.chips[label] = chip
            row.addWidget(chip)
        row.addStretch(1)

        self.send = QPushButton("Ask")
        self.send.setProperty("accent", True)
        self.send.setIcon(icon("send", "#FFFFFF"))
        self.send.setIconSize(QSize(18, 18))
        self.send.clicked.connect(self._submit)
        row.addWidget(self.send)
        layout.addLayout(row)

        # Enter submits, Shift+Enter newline
        sc = QShortcut(QKeySequence(Qt.Key_Return), self.box)
        sc.activated.connect(self._submit)
        sc2 = QShortcut(QKeySequence(Qt.Key_Enter), self.box)
        sc2.activated.connect(self._submit)

    def _fill(self, text: str):
        self.box.setText(text)
        self.box.setFocus()

    def _submit(self):
        text = self.box.toPlainText().strip()
        if text:
            self.submitted.emit(text)

    def set_loading(self, loading: bool):
        self.send.setEnabled(not loading)
        self.box.setReadOnly(loading)
        if loading:
            self.send.setText("Thinking…")
        else:
            self.send.setText("Ask")

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self.send.setIcon(icon("send", "#FFFFFF"))
