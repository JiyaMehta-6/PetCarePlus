"""Pet profile card and editor widget."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QDialogButtonBox,
)
from app.ui.theme import get_palette
from app.ui.components.illustrations import SpeciesMark
from app.ui.components.icons import icon
from app.rag.species_registry import SPECIES, SPECIES_BY_KEY


class PetProfileCard(QWidget):
    selected = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, pet: dict, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self.pet = pet
        self._palette_name = palette_name
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.mark = SpeciesMark(self._palette_name)
        layout.addWidget(self.mark)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(self.pet.get("name", "Pet"))
        name.setObjectName("primaryLabel")
        meta = QLabel()
        bits = []
        if self.pet.get("species_display"):
            bits.append(self.pet["species_display"])
        if self.pet.get("breed"):
            bits.append(self.pet["breed"])
        if self.pet.get("age_years") not in (None, ""):
            bits.append(f"{self.pet['age_years']} yr")
        meta.setText(" · ".join(bits))
        meta.setObjectName("muted")
        meta.setStyleSheet("font-size: 8pt;")
        info.addWidget(name)
        info.addWidget(meta)
        layout.addLayout(info, 1)

        self.active = QLabel()
        self.active.setFixedHeight(16)
        layout.addWidget(self.active)
        self._update_active_label()

        del_btn = QPushButton()
        del_btn.setIcon(icon("delete", get_palette(self._palette_name).muted))
        del_btn.setFlat(True)
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda: self.deleteRequested.emit(self.pet.get("id")))
        layout.addWidget(del_btn)

    def mousePressEvent(self, ev):
        self.selected.emit(self.pet.get("id"))

    def set_active_state(self, active: bool):
        # Update the active indicator without rebuilding the widget, so the
        # card never moves/resizes when selected.
        self.pet["active"] = active
        self._update_active_label()

    def _update_active_label(self):
        # Constant-height status row so toggling active never resizes the card
        # (which would otherwise make it jump/shift in the list).
        p = get_palette(self._palette_name)
        if self.pet.get("active"):
            self.active.setText("● Active profile")
            self.active.setStyleSheet(f"color: {p.success}; font-size: 8pt; font-weight: 600;")
        else:
            self.active.setText("Tap card to set as active")
            self.active.setStyleSheet(f"color: {p.muted}; font-size: 8pt;")

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self.mark.set_theme(palette_name)
        self._update_active_label()


class PetProfileEditor(QDialog):
    """Add / edit a pet profile (no photos required)."""

    def __init__(self, pet: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pet profile" if pet is None else "Edit pet")
        self.setMinimumWidth(380)
        self.pet = pet or {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.name = QLineEdit(self.pet.get("name", ""))
        self.species = QComboBox()
        self.species.addItem("— select —", "")
        for s in SPECIES:
            self.species.addItem(f"{s.display}  ({s.group})", s.key)
        if self.pet.get("species_key"):
            idx = self.species.findData(self.pet.get("species_key"))
            if idx >= 0:
                self.species.setCurrentIndex(idx)
        self.breed = QComboBox()
        self.breed.setEditable(True)
        self.species.currentIndexChanged.connect(self._populate_breeds)
        self._populate_breeds()
        self.age = QDoubleSpinBox()
        self.age.setRange(0, 40)
        self.age.setSuffix(" yr")
        if self.pet.get("age_years") not in (None, ""):
            try:
                self.age.setValue(float(self.pet["age_years"]))
            except (TypeError, ValueError):
                pass
        self.sex = QComboBox()
        self.sex.addItems(["", "Male", "Female"])
        if self.pet.get("sex"):
            self.sex.setCurrentText(self.pet["sex"])
        self.notes = QTextEdit(self.pet.get("notes", ""))
        self.notes.setFixedHeight(60)

        form.addRow("Name", self.name)
        form.addRow("Species", self.species)
        form.addRow("Breed", self.breed)
        form.addRow("Age", self.age)
        form.addRow("Sex", self.sex)
        form.addRow("Notes", self.notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_breeds(self) -> None:
        """Fill the breed box with breeds that belong to the chosen species.

        The breed field is contextual: when a species has known breeds (e.g.
        Labrador -> 'Labrador Retriever') those are offered as suggestions, and
        the first is pre-selected so the box is never a confusing blank. The box
        stays editable for mixes / variants. Species with no curated breeds
        leave it open for free text.
        """
        key = self.species.currentData()
        self.breed.clear()
        self.breed.addItem("")  # unspecified / mixed
        breeds = []
        if key:
            sp = SPECIES_BY_KEY.get(key)
            if sp and sp.breeds:
                breeds = sp.breeds
        for b in breeds:
            self.breed.addItem(b)
        # For a species with a single known breed there is no real choice, so
        # pre-select it; otherwise leave the blank so the user picks/confirms.
        if len(breeds) == 1:
            self.breed.setCurrentIndex(1)
        # Restore a previously entered value, if editing an existing profile.
        existing = self.pet.get("breed", "")
        if existing:
            idx = self.breed.findText(existing)
            if idx >= 0:
                self.breed.setCurrentIndex(idx)
            else:
                self.breed.setEditText(existing)

    def data(self) -> dict:
        key = self.species.currentData()
        disp = ""
        if key:
            sp = SPECIES_BY_KEY.get(key)
            disp = sp.display if sp else ""
        return {
            "name": self.name.text().strip(),
            "species_key": key or "",
            "species_display": disp,
            "breed": self.breed.currentText().strip(),
            "age_years": self.age.value() if self.age.value() > 0 else None,
            "sex": self.sex.currentText(),
            "notes": self.notes.toPlainText().strip(),
        }
