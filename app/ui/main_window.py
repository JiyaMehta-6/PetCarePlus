"""PetCare+ main window and view orchestration."""

from __future__ import annotations

import json
import time

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QStackedWidget, QSizePolicy, QTextEdit,
)
from PySide6.QtGui import QClipboard

from app.config import configure_caches, ensure_root, ensure_directories, PETCARE_ROOT
from app.log_utils import setup_logging, get_logger
from app.storage.local_store import LocalStore
from app.ui.theme import get_palette, build_qss
from app.ui.components import (
    AppShell, QueryInput, AnswerCard, LoadingState, EmptyState, RetrievalStatus,
    PetProfileCard, PetProfileEditor, SettingsPanel, CareConstellation, KnowledgePulse,
)
from app.ui.components.icons import logo_icon, logo_pixmap, icon

logger = get_logger("petcare.ui")


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
class AnswerWorker(QThread):
    token = Signal(str)
    stage = Signal(str)
    done = Signal(object)  # Answer
    error = Signal(str)

    def __init__(self, engine, query, pet_profile=None, history=None):
        super().__init__()
        self.engine = engine
        self.query = query
        self.pet_profile = pet_profile
        self.history = history

    def run(self):
        try:
            ans = self.engine.answer(
                self.query,
                pet_profile=self.pet_profile,
                history=self.history,
                on_token=self.token.emit,
                on_stage=self.stage.emit,
            )
            self.done.emit(ans)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Answer worker failed")
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class HomeView(QWidget):
    ask = Signal(str)

    def __init__(self, palette_name: str, store: LocalStore, parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.store = store
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(18)

        top = QHBoxLayout()
        hero = QVBoxLayout()
        hero.setSpacing(6)
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(logo_pixmap(46))
        mark.setFixedSize(48, 48)
        mark.setStyleSheet("background: transparent;")
        self._hero_title = QLabel("PetCare+")
        self._hero_title.setObjectName("title")
        self._hero_sub = QLabel("Understand them better.\nCare for them smarter.")
        self._hero_sub.setObjectName("subtitle")
        self._hero_tag = QLabel("Evidence-grounded pet care, powered locally.")
        self._hero_tag.setObjectName("muted")
        title_row.addWidget(mark)
        title_row.addWidget(self._hero_title)
        title_row.addStretch(1)
        hero.addLayout(title_row)
        hero.addWidget(self._hero_sub)
        hero.addWidget(self._hero_tag)
        self._apply_hero_theme()
        top.addLayout(hero)
        top.addStretch(1)
        self.constellation = CareConstellation()
        self.constellation.setFixedSize(240, 150)
        self.constellation.set_theme(self._palette_name)
        top.addWidget(self.constellation)
        root.addLayout(top)

        root.addWidget(self._divider())

        # Query
        self.query = QueryInput(self._palette_name)
        self.query.submitted.connect(self.ask.emit)
        root.addWidget(self.query)

        self.status = RetrievalStatus(self._palette_name)
        root.addWidget(self.status)

        self.answer_inner = QWidget()
        self.answer_layout = QVBoxLayout(self.answer_inner)
        self.answer_layout.setSpacing(12)
        self.answer_layout.setContentsMargins(0, 0, 0, 0)
        self.answer_scroll = ScrollView(self.answer_inner)
        self.answer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.answer_widget = EmptyState(
            "Your caring companion",
            "Ask about nutrition, symptoms, grooming, behaviour or anything pet-related.\n"
            "Answers are grounded in a local knowledge base and never require the internet.",
            self._palette_name,
        )
        self.answer_layout.insertWidget(0, self.answer_widget)
        root.addWidget(self.answer_scroll, 1)

        self._worker: AnswerWorker | None = None
        self._engine = None
        self._active_pet = None
        self._history = []

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setObjectName("divider")
        f.setFixedHeight(1)
        return f

    def set_engine(self, engine):
        self._engine = engine

    def set_active_pet(self, pet):
        self._active_pet = pet

    def show_answer(self, answer):
        # replace answer widget
        old = self.answer_widget
        new = AnswerCard(answer, self._palette_name)
        self.answer_layout.replaceWidget(old, new)
        old.deleteLater()
        self.answer_widget = new
        self._last_answer = answer
        self.answer_scroll.verticalScrollBar().setValue(0)
        self.status.set_text(answer.retrieval_report)
        # persist to history
        from app.storage.local_store import ConversationTurn
        self.store.append_turn(ConversationTurn(
            query=answer.query,
            answer=answer.answer_text,
            sources=[s.to_dict() for s in answer.sources],
            safety_level=answer.safety.level if answer.safety else "none",
            confidence=answer.confidence,
        ))

    def show_loading(self, query):
        old = self.answer_widget
        # Live-streaming container: a spinner on top + a text area that fills
        # with the generated answer as tokens arrive, so the UI never looks frozen.
        self._stream_buf = ""
        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)
        self.loading = LoadingState(self._palette_name)
        cl.addWidget(self.loading)
        self._stream_text = QTextEdit()
        self._stream_text.setReadOnly(True)
        self._stream_text.setPlainText("Thinking…")
        self._stream_text.setStyleSheet(
            "border: none; background: transparent; font-size: 13.5px;"
        )
        self._stream_text.setMaximumHeight(400)
        cl.addWidget(self._stream_text)
        self.answer_layout.replaceWidget(old, container)
        old.deleteLater()
        self.answer_widget = container

    def append_stream(self, text: str):
        if getattr(self, "_stream_text", None) is None:
            return
        self._stream_buf += text
        self._stream_text.setPlainText(self._stream_buf)

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self._apply_hero_theme()
        self.query.set_theme(palette_name)
        self.constellation.set_theme(palette_name)
        # rebuild answer widget if it's an AnswerCard
        if isinstance(self.answer_widget, AnswerCard) and getattr(self, "_last_answer", None):
            self.show_answer(self._last_answer)

    def _apply_hero_theme(self):
        from app.ui.theme import get_palette

        p = get_palette(self._palette_name)
        self._hero_title.setStyleSheet(
            f"font-size: 30pt; color: {p.primary}; letter-spacing: -1px;"
        )
        self._hero_sub.setStyleSheet(f"font-size: 15pt; color: {p.secondary};")
        self._hero_tag.setStyleSheet(f"font-size: 10pt; color: {p.muted};")


class PetsView(QWidget):
    def __init__(self, palette_name: str, store: LocalStore, parent=None):
        super().__init__(parent)
        self._palette_name = palette_name
        self.store = store
        self.on_select = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(14)
        head = QHBoxLayout()
        t = QLabel("Your pets")
        t.setObjectName("title")
        t.setStyleSheet("font-size: 18pt;")
        head.addWidget(t)
        head.addStretch(1)
        add = QPushButton("+ Add pet")
        add.setProperty("primary", True)
        add.clicked.connect(self._add)
        head.addWidget(add)
        root.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(10)
        self.scroll.setWidget(self.list_widget)
        root.addWidget(self.scroll, 1)
        self.refresh()

    def refresh(self):
        self._cards = {}
        for i in reversed(range(self.list_layout.count())):
            w = self.list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        pets = self.store.load_pets()
        if not pets:
            self.list_layout.addStretch(1)
            self.list_layout.addWidget(EmptyState(
                "No pets yet",
                "Add a pet profile to personalise retrieval (species, breed, age).",
                self._palette_name,
            ))
            self.list_layout.addStretch(1)
        else:
            for pet in pets:
                card = PetProfileCard(pet.__dict__, self._palette_name)
                card.selected.connect(self._selected)
                card.deleteRequested.connect(self._delete)
                self.list_layout.addWidget(card)
                self._cards[pet.id] = card
            self.list_layout.addStretch(1)

    def _sync_active_states(self):
        # Update the active indicator on existing cards in place (no rebuild),
        # so selecting a pet never moves or resizes its card.
        active_ids = {p.id for p in self.store.load_pets() if p.active}
        for cid, card in self._cards.items():
            card.set_active_state(cid in active_ids)

    def _add(self):
        dlg = PetProfileEditor()
        if dlg.exec():
            data = dlg.data()
            if data["name"]:
                from app.storage.local_store import PetProfile
                self.store.add_pet(PetProfile(**data))
                self.refresh()
                self.scroll.verticalScrollBar().setValue(0)
                # Keep the query context (home._active_pet) in sync, e.g. when the
                # first pet is auto-activated it must immediately drive retrieval.
                if self.on_select:
                    self.on_select()

    def _selected(self, pid):
        # "Set as active": the clicked pet becomes the sole active profile.
        # Never toggle an active pet off (that would silently drop all pet
        # context from retrieval) -- re-tapping the active card is a no-op.
        pets = self.store.load_pets()
        for p in pets:
            p.active = (p.id == pid)
        if pets:
            self.store.save_pets(pets)
        self._sync_active_states()
        if self.on_select:
            self.on_select()

    def _delete(self, pid):
        self.store.delete_pet(pid)
        self.refresh()
        if self.on_select:
            self.on_select()

    def set_theme(self, palette_name: str):
        self._palette_name = palette_name
        self.refresh()


class ScrollView(QScrollArea):
    """Generic scrollable container holding a single widget."""

    def __init__(self, widget: QWidget, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setWidget(widget)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        configure_caches()
        ensure_directories()
        setup_logging()
        self.store = LocalStore()
        self.settings = self.store.load_settings()
        self._palette_name = self.settings.get("appearance", "Light").lower()
        self._apply_theme()
        self._connect_system_theme()

        self.setWindowTitle("PetCare+")
        self.setWindowIcon(logo_icon())
        self.resize(1200, 800)
        self.setMinimumSize(960, 650)

        self.engine = None
        self._init_engine()

        self.shell = AppShell(self._palette_name)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.shell)

        self._build_views()
        self.shell.sidebar.navRequested.connect(self._nav)

    # -- engine ----------------------------------------------------------
    def _init_engine(self):
        try:
            from app.rag.engine import RAGEngine
            self.engine = RAGEngine()
            # Load index + embedder eagerly; generation lazily (heavy).
            self.engine.initialize(load_generation=False)
        except Exception as exc:
            logger.exception("Engine init failed")
            self.engine = None

    # -- views -----------------------------------------------------------
    def _build_views(self):
        pal = self._palette_name
        self.home = HomeView(pal, self.store)
        self.home.set_engine(self.engine)
        self.home.ask.connect(self._on_ask)
        self.home._active_pet = self._active_pet_dict()
        self.shell.add_view("home", self.home)

        self.pets = PetsView(pal, self.store)
        self.pets.on_select = self._refresh_active_pet
        # PetsView already contains its own scroll area; add it directly.
        self.shell.add_view("pets", self.pets)

        self.knowledge = self._knowledge_view()
        self.shell.add_view("knowledge", ScrollView(self.knowledge))

        self.sources = self._sources_view()
        self.shell.add_view("sources", ScrollView(self.sources))

        self.history = self._history_view()
        self.shell.add_view("history", ScrollView(self.history))

        self.settings_panel = SettingsPanel(self.settings, pal)
        self.settings_panel.changed.connect(self._on_settings)
        self.settings_panel.appearanceChanged.connect(self._on_appearance_live)
        self.shell.add_view("settings", ScrollView(self.settings_panel))

        self.shell.show_view("home", 0)
        self.shell.sidebar.set_active("home")

    def _active_pet_dict(self):
        p = self.store.get_active_pet()
        return p.__dict__ if p else None

    def _refresh_active_pet(self):
        self.home._active_pet = self._active_pet_dict()
        self.home.set_active_pet(self.home._active_pet)

    # -- navigation ------------------------------------------------------
    def _nav(self, key):
        idx = {"home": 0, "pets": 1, "knowledge": 2, "sources": 3, "history": 4, "settings": 5}[key]
        if key == "pets":
            self.pets.refresh()
        elif key == "history":
            self._rebuild_history()
        self.shell.show_view(key, idx)
        self.shell.sidebar.set_active(key)

    # -- ask -------------------------------------------------------------
    def _on_ask(self, query):
        if not self.engine:
            self.home.status.set_text("Knowledge engine unavailable.")
            return
        self.home.show_loading(query)
        pet = self._resolve_pet_for_query(query)
        self._worker = AnswerWorker(self.engine, query, pet_profile=pet, history=None)
        self._worker.token.connect(self.home.append_stream)
        self._worker.stage.connect(self.home.loading.set_stage)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _resolve_pet_for_query(self, query: str) -> dict | None:
        """Prefer the active pet, but fall back to a pet whose name appears in
        the query so 'why is daisy not eating' is answered for Daisy."""
        active = self.home._active_pet
        if active:
            return active
        ql = (query or "").lower()
        for p in self.store.load_pets():
            name = (p.name or "").lower().strip()
            if name and name in ql:
                return p.__dict__
        return None

    def _on_done(self, answer):
        self.home._last_answer = answer
        self.home.show_answer(answer)

    def _on_error(self, msg):
        from app.rag.engine import Answer
        a = Answer(query="", answer_text=f"Something went wrong: {msg}")
        self.home.show_answer(a)

    # -- static views ----------------------------------------------------
    def _knowledge_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)
        t = QLabel("Knowledge base")
        t.setObjectName("title"); t.setStyleSheet("font-size: 18pt;")
        layout.addWidget(t)
        from app.rag.knowledge import chunk_count
        n = chunk_count()
        info = QLabel(
            f"{n} curated, semantically chunked entries across 30 pet types.\n"
            "Hybrid retrieval (dense BGE-small + BM25) fused with Reciprocal Rank Fusion. "
            "Dogs and cats use species + breed-level knowledge; exotic pets are covered "
            "with species-specific care. Fully offline after build."
        )
        info.setObjectName("subtitle"); info.setWordWrap(True)
        layout.addWidget(info)
        cats = QLabel(
            "Categories: Nutrition · Environment · Grooming · Behaviour · Exercise · "
            "Preventive care · Health · India-specific guidance."
        )
        cats.setObjectName("muted"); cats.setWordWrap(True)
        layout.addWidget(cats)
        layout.addStretch(1)
        return w

    def _sources_view(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)
        t = QLabel("Sources & authorities")
        t.setObjectName("title"); t.setStyleSheet("font-size: 18pt;")
        layout.addWidget(t)
        items = [
            ("WSAVA", "Global Nutrition & Vaccination Guidelines", "veterinary_guideline"),
            ("Merck Veterinary Manual", "Open veterinary reference", "veterinary_manual"),
            ("Animal Welfare Board of India", "Government", "government"),
            ("Dept. of Animal Husbandry & Dairying, GoI", "Government", "government"),
            ("National Centre for Disease Control, India", "Rabies / public health", "government"),
            ("AVMA", "Veterinary association", "veterinary_association"),
            ("India Meteorological Department", "Climate guidance", "government"),
        ]
        for name, desc, auth in items:
            c = QFrame(); c.setObjectName("Card")
            cl = QVBoxLayout(c); cl.setContentsMargins(14, 10, 14, 10); cl.setSpacing(2)
            cl.addWidget(QLabel(name))
            d = QLabel(f"{desc} · {auth}")
            d.setObjectName("muted"); d.setStyleSheet("font-size: 8pt;")
            cl.addWidget(d)
            layout.addWidget(c)
        layout.addStretch(1)
        return w

    def _history_view(self) -> QWidget:
        self._history_widget = QWidget()
        self._history_layout = QVBoxLayout(self._history_widget)
        self._history_layout.setContentsMargins(30, 24, 30, 24)
        self._history_layout.setSpacing(12)
        self._rebuild_history()
        return self._history_widget

    def _clear_history_layout(self):
        # Remove EVERYTHING currently in the history layout -- widgets, nested
        # layouts (e.g. the header) and spacers. Deleting only widgets left the
        # header layout accumulating on every rebuild, duplicating the
        # "Clear history" button.
        while self._history_layout.count():
            item = self._history_layout.takeAt(0)
            if item is None:
                continue
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    ci = sub.takeAt(0)
                    if ci is not None and ci.widget() is not None:
                        ci.widget().deleteLater()
                sub.deleteLater()
            elif item.widget() is not None:
                item.widget().deleteLater()
            # spacer items are simply dropped

    def _rebuild_history(self):
        self._clear_history_layout()
        self._history_cards = {}
        turns = self.store.load_conversations()

        # Header: title + clear-all action.
        header = QHBoxLayout()
        t = QLabel("Conversation history")
        t.setObjectName("title"); t.setStyleSheet("font-size: 18pt;")
        header.addWidget(t)
        header.addStretch(1)
        clear_btn = QPushButton("Clear history")
        clear_btn.setIcon(icon("delete", get_palette(self._palette_name).muted))
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)
        self._history_layout.addLayout(header)

        if not turns:
            self._history_layout.addStretch(1)
            self._history_layout.addWidget(EmptyState("No history yet",
                "Your local conversations will appear here.", self._palette_name))
            self._history_layout.addStretch(1)
            return
        for turn in reversed(turns[-50:]):
            c = QFrame(); c.setObjectName("Card")
            self._history_cards[turn.id] = c
            cl = QVBoxLayout(c); cl.setContentsMargins(14, 10, 14, 10); cl.setSpacing(4)
            row = QHBoxLayout()
            q = QLabel(f"Q: {turn.query}")
            q.setObjectName("primaryLabel"); q.setStyleSheet("font-size: 10pt;")
            row.addWidget(q, 1)
            del_btn = QPushButton()
            del_btn.setIcon(icon("delete", get_palette(self._palette_name).muted))
            del_btn.setFlat(True)
            del_btn.setFixedSize(26, 26)
            del_btn.setToolTip("Delete this conversation")
            del_btn.clicked.connect(
                lambda _=None, tid=turn.id: self._delete_turn(tid)
            )
            row.addWidget(del_btn)
            cl.addLayout(row)
            a = QLabel(turn.answer[:200] + ("…" if len(turn.answer) > 200 else ""))
            a.setObjectName("muted"); a.setWordWrap(True); a.setStyleSheet("font-size: 8pt;")
            cl.addWidget(a)
            self._history_layout.addWidget(c)
        self._history_layout.addStretch(1)

    def _delete_turn(self, turn_id: str):
        self.store.delete_turn(turn_id)
        card = getattr(self, "_history_cards", {}).pop(turn_id, None)
        if card is not None:
            card.deleteLater()
        # Only do a full rebuild when the last entry is gone (so we show the empty
        # state); otherwise just remove that one card in place to avoid a reflow of
        # every other card.
        if not getattr(self, "_history_cards", {}):
            self._rebuild_history()

    def _clear_history(self):
        self.store.clear_conversations()
        self._rebuild_history()

    # -- settings --------------------------------------------------------
    def _on_settings(self, settings):
        self.settings = settings
        self.store.save_settings(settings)
        pal = settings.get("appearance", "Light").lower()
        if pal != self._palette_name:
            self._palette_name = pal
            self._apply_theme()
            self._rebuild_all_themes()

    def _apply_theme(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_qss(get_palette(self._palette_name)))

    def _connect_system_theme(self):
        # Re-apply instantly when the OS colour scheme changes (only matters if
        # the user picked "System").
        try:
            from PySide6.QtGui import QGuiApplication

            hints = QGuiApplication.styleHints()
            if hints is not None:
                hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        except Exception:
            pass

    def _on_system_theme_changed(self):
        if self._palette_name == "system":
            self._apply_theme()
            self._rebuild_all_themes()

    def _on_appearance_live(self, appearance: str):
        # Apply the theme immediately as the user changes the dropdown so the UI
        # updates without requiring "Save settings", and persist the choice.
        pal = (appearance or "Light").lower()
        if pal == self._palette_name:
            return
        self._palette_name = pal
        self._apply_theme()
        self.home.set_theme(pal)
        self.pets.set_theme(pal)
        self.shell.set_theme(pal)
        self._rebuild_history()
        self.settings["appearance"] = appearance
        self.store.save_settings(self.settings)

    def _rebuild_all_themes(self):
        self.home.set_theme(self._palette_name)
        self.pets.set_theme(self._palette_name)
        self.shell.set_theme(self._palette_name)
        self._rebuild_history()
        # rebuild sources/knowledge scroll contents
        self.shell.stack.widget(2).setWidget(self._knowledge_view())
        self.shell.stack.widget(3).setWidget(self._sources_view())
        new_settings = SettingsPanel(self.settings, self._palette_name)
        new_settings.changed.connect(self._on_settings)
        self.shell.stack.widget(5).setWidget(ScrollView(new_settings))

    def closeEvent(self, ev):
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
        super().closeEvent(ev)
