"""Local, private storage for PetCare+.

Everything lives under the D: drive data directory. No cloud, no accounts.
Pet profiles, conversation history and user settings are stored as plain JSON.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.config import PETS_DIR, CONVERSATIONS_DIR, DATA_DIR
from app.log_utils import get_logger

logger = get_logger("petcare.storage")


@dataclass
class PetProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    species_key: str = ""
    species_display: str = ""
    breed: str = ""
    age_years: float | None = None
    sex: str = ""
    notes: str = ""
    photo_path: str = ""
    active: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class ConversationTurn:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    answer: str = ""
    sources: list = field(default_factory=list)
    safety_level: str = "none"
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class LocalStore:
    def __init__(self):
        PETS_DIR.mkdir(parents=True, exist_ok=True)
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.pets_file = PETS_DIR / "profiles.json"
        self.conv_file = CONVERSATIONS_DIR / "history.jsonl"
        self.settings_file = DATA_DIR / "settings.json"

    # ---- pets --------------------------------------------------------
    def load_pets(self) -> list[PetProfile]:
        if not self.pets_file.exists():
            return []
        try:
            data = json.loads(self.pets_file.read_text(encoding="utf-8"))
            return [PetProfile(**p) for p in data]
        except Exception as err:
            logger.warning("Failed to load pets: %s", err)
            return []

    def save_pets(self, pets: list[PetProfile]) -> None:
        self.pets_file.write_text(
            json.dumps([asdict(p) for p in pets], indent=2), encoding="utf-8"
        )

    def add_pet(self, pet: PetProfile) -> None:
        pets = self.load_pets()
        if pet.active:
            for p in pets:
                p.active = False
        elif not pets:
            # The first pet added becomes the active profile automatically.
            pet.active = True
        pets.insert(0, pet)
        self.save_pets(pets)

    def update_pet(self, pet: PetProfile) -> None:
        pets = self.load_pets()
        for i, p in enumerate(pets):
            if p.id == pet.id:
                if pet.active:
                    for other in pets:
                        other.active = False
                    pet.active = True
                pets[i] = pet
                break
        self.save_pets(pets)

    def delete_pet(self, pet_id: str) -> None:
        pets = [p for p in self.load_pets() if p.id != pet_id]
        self.save_pets(pets)

    def get_active_pet(self) -> PetProfile | None:
        pets = self.load_pets()
        for p in pets:
            if p.active:
                return p
        return None

    # ---- conversations ----------------------------------------------
    def append_turn(self, turn: ConversationTurn) -> None:
        with self.conv_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(turn)) + "\n")

    def load_conversations(self) -> list[ConversationTurn]:
        if not self.conv_file.exists():
            return []
        turns = []
        for line in self.conv_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                turns.append(ConversationTurn(**json.loads(line)))
            except Exception:
                continue
        return turns

    def delete_turn(self, turn_id: str) -> None:
        turns = [t for t in self.load_conversations() if t.id != turn_id]
        self.conv_file.write_text(
            "\n".join(json.dumps(asdict(t)) for t in turns), encoding="utf-8"
        )

    def clear_conversations(self) -> None:
        if self.conv_file.exists():
            self.conv_file.write_text("", encoding="utf-8")

    # ---- settings ----------------------------------------------------
    def load_settings(self) -> dict[str, Any]:
        defaults = {
            "appearance": "light",          # light | dark | system
            "generation_model": "Qwen2.5-3B-Instruct",
            "embedding_model": "BGE-small-en-v1.5",
            "mode": "Local",
            "local_processing": True,
            "cloud_services": "None",
            "conversation_storage": "Local",
            "streaming": True,
        }
        if not self.settings_file.exists():
            return defaults
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            defaults.update(data)
        except Exception:
            pass
        return defaults

    def save_settings(self, settings: dict[str, Any]) -> None:
        self.settings_file.write_text(
            json.dumps(settings, indent=2), encoding="utf-8"
        )
