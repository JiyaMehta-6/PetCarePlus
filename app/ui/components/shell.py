"""Application shell: sidebar navigation and the main content container."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QFrame,
)
from app.ui.theme import get_palette
from app.ui.components.icons import icon, logo_pixmap


class Sidebar(QWidget):
    navRequested = Signal(str)

    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._palette_name = palette_name
        self._buttons: dict[str, QPushButton] = {}
        self._build()

    def _nav_button(self, key: str, label: str, icon_name: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("nav", True)
        btn.setProperty("active", False)
        btn.setIcon(icon(icon_name, self._color()))
        btn.setIconSize(QSize(20, 20))
        btn.setText(f"  {label}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.navRequested.emit(key))
        self._buttons[key] = btn
        return btn

    def _color(self) -> str:
        return get_palette(self._palette_name).primary

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(6)

        logo = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(logo_pixmap(32))
        mark.setFixedSize(34, 34)
        mark.setStyleSheet("background: transparent;")
        title = QLabel("PetCare+")
        title.setObjectName("primaryLabel")
        title.setStyleSheet("font-size: 14pt;")
        logo.addWidget(mark)
        logo.addWidget(title)
        logo.addStretch(1)
        layout.addLayout(logo)

        sub = QLabel("Evidence-grounded pet care,\npowered locally.")
        sub.setObjectName("SidebarLabel")
        sub.setStyleSheet("font-size: 8pt; padding: 4px 2px 12px 2px;")
        layout.addWidget(sub)

        layout.addWidget(self._divider())

        for key, (label, ic) in [
            ("home", ("Home", "home")),
            ("pets", ("Your pets", "pets")),
            ("knowledge", ("Knowledge", "book")),
            ("sources", ("Sources", "sources")),
            ("history", ("History", "history")),
            ("settings", ("Settings", "settings")),
        ]:
            layout.addWidget(self._nav_button(key, label, ic))

        layout.addStretch(1)

        foot = QLabel("Local · Offline · Private")
        foot.setObjectName("SidebarLabel")
        foot.setStyleSheet("font-size: 8pt; padding-top: 8px;")
        layout.addWidget(foot)

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setObjectName("divider")
        f.setFixedHeight(1)
        return f

    def set_active(self, key: str):
        for k, b in self._buttons.items():
            b.setProperty("active", k == key)
            b.style().polish(b)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        col = self._color()
        for b in self._buttons.values():
            b.setIcon(icon(b.icon().name() if False else self._btn_icon(b), col))
            b.style().polish(b)

    def _btn_icon(self, b) -> str:
        # map by text
        txt = b.text().strip()
        mapping = {
            "Home": "home", "Your pets": "pets", "Knowledge": "book",
            "Sources": "sources", "History": "history", "Settings": "settings",
        }
        return mapping.get(txt, "home")


class AppShell(QWidget):
    """Holds the sidebar and a stacked content area."""

    def __init__(self, palette_name: str = "light", parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        self.sidebar = Sidebar(palette_name)
        root.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

    def add_view(self, name: str, widget: QWidget):
        self.stack.addWidget(widget)

    def show_view(self, name: str, index: int):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(name)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self.sidebar.set_theme(palette_name)
