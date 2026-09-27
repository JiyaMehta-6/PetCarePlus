"""Settings panel."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox, QPushButton, QFormLayout,
)
from app.ui.theme import get_palette


class SettingsPanel(QWidget):
    changed = Signal(dict)
    appearanceChanged = Signal(str)

    def __init__(self, settings: dict, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.settings = dict(settings)
        self._build()

    def _card(self, title: str) -> QFrame:
        c = QFrame()
        c.setObjectName("Card")
        layout = QVBoxLayout(c)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("primaryLabel")
        t.setStyleSheet("font-size: 11pt;")
        layout.addWidget(t)
        c._form = QFormLayout()
        c._form.setSpacing(10)
        layout.addLayout(c._form)
        return c

    def _add(self, card, label, widget):
        card._form.addRow(label, widget)

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(0, 0, 0, 0)

        appearance = self._card("Appearance")
        self.appearance = QComboBox()
        self.appearance.addItems(["Light", "Dark", "System"])
        self.appearance.setCurrentText(self.settings.get("appearance", "Light"))
        self.appearance.currentTextChanged.connect(self.appearanceChanged.emit)
        self._add(appearance, "Theme", self.appearance)
        root.addWidget(appearance)

        ai = self._card("AI")
        self.gen = QComboBox()
        self.gen.addItems(["Qwen2.5-3B-Instruct", "Qwen2.5-1.5B-Instruct"])
        self.gen.setCurrentText(self.settings.get("generation_model", "Qwen2.5-3B-Instruct"))
        self.emb = QComboBox()
        self.emb.addItems(["BGE-small-en-v1.5"])
        self.emb.setCurrentText(self.settings.get("embedding_model", "BGE-small-en-v1.5"))
        self.mode = QComboBox()
        self.mode.addItems(["Local"])
        self.mode.setCurrentText(self.settings.get("mode", "Local"))
        self._add(ai, "Generation", self.gen)
        self._add(ai, "Embeddings", self.emb)
        self._add(ai, "Mode", self.mode)
        root.addWidget(ai)

        priv = self._card("Privacy")
        self.local_proc = QLabel("On")
        self.cloud = QLabel("None")
        self.conv_store = QLabel("Local")
        self._add(priv, "Local processing", self.local_proc)
        self._add(priv, "Cloud services", self.cloud)
        self._add(priv, "Conversation storage", self.conv_store)
        root.addWidget(priv)

        about = self._card("About")
        a = QLabel("PetCare+\nEvidence-grounded pet care, powered locally.\nNo paid APIs. Fully offline after setup.")
        a.setObjectName("muted")
        a.setStyleSheet("font-size: 9pt;")
        about._form.addRow(a)
        root.addWidget(about)

        root.addStretch(1)
        save = QPushButton("Save settings")
        save.setProperty("primary", True)
        save.clicked.connect(self._save)
        root.addWidget(save)

    def _save(self):
        self.settings.update({
            "appearance": self.appearance.currentText(),
            "generation_model": self.gen.currentText(),
            "embedding_model": self.emb.currentText(),
            "mode": self.mode.currentText(),
        })
        self.changed.emit(self.settings)
