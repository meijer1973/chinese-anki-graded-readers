from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
ANKI_CONNECT_VERSION = 6


class AnkiConnectError(RuntimeError):
    """Raised when AnkiConnect is unavailable or rejects a request."""


class MutationSafetyError(RuntimeError):
    """Raised before a mutation that crosses the Hindi-only boundary."""


class Transport(Protocol):
    def __call__(self, action: str, params: dict[str, Any] | None = None) -> Any: ...


class HttpTransport:
    def __init__(self, url: str = ANKI_CONNECT_URL, timeout: float = 60.0) -> None:
        self.url = url
        self.timeout = timeout

    def __call__(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"action": action, "version": ANKI_CONNECT_VERSION}
        if params is not None:
            payload["params"] = params
        request = Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise AnkiConnectError(f"AnkiConnect request {action!r} failed: {exc}") from exc
        if data.get("error"):
            raise AnkiConnectError(f"AnkiConnect {action!r}: {data['error']}")
        return data.get("result")


@dataclass
class MutationGuard:
    hindi_deck: str
    hindi_model: str
    hindi_preset: str
    protected_deck: str
    protected_model: str
    protected_note_ids: set[int] = field(default_factory=set)
    protected_card_ids: set[int] = field(default_factory=set)
    protected_config_ids: set[int] = field(default_factory=set)
    hindi_note_ids: set[int] = field(default_factory=set)
    hindi_card_ids: set[int] = field(default_factory=set)
    hindi_config_ids: set[int] = field(default_factory=set)

    def register_hindi_notes(self, note_ids: list[int] | set[int]) -> None:
        self.hindi_note_ids.update(int(value) for value in note_ids)

    def register_hindi_cards(self, card_ids: list[int] | set[int]) -> None:
        self.hindi_card_ids.update(int(value) for value in card_ids)

    def register_hindi_config(self, config_id: int) -> None:
        config_id = int(config_id)
        if config_id in self.protected_config_ids:
            raise MutationSafetyError(f"configuration ID {config_id} is protected")
        self.hindi_config_ids.add(config_id)

    def _guard_note_ids(self, values: list[int]) -> None:
        note_ids = {int(value) for value in values}
        if note_ids & self.protected_note_ids:
            raise MutationSafetyError("attempted mutation of a protected Chinese note ID")
        unknown = note_ids - self.hindi_note_ids
        if unknown:
            raise MutationSafetyError(f"attempted mutation of unregistered note IDs: {sorted(unknown)[:10]}")

    def _guard_card_ids(self, values: list[int]) -> None:
        card_ids = {int(value) for value in values}
        if card_ids & self.protected_card_ids:
            raise MutationSafetyError("attempted mutation of a protected Chinese card ID")
        unknown = card_ids - self.hindi_card_ids
        if unknown:
            raise MutationSafetyError(f"attempted mutation of unregistered card IDs: {sorted(unknown)[:10]}")

    def validate(self, action: str, params: dict[str, Any] | None) -> None:
        params = params or {}
        if action == "multi":
            for nested in params.get("actions", []):
                self.validate(str(nested.get("action", "")), nested.get("params"))
            return

        if action == "createDeck":
            if params.get("deck") != self.hindi_deck:
                raise MutationSafetyError("createDeck may target only the Hindi deck")
        elif action == "createModel":
            if params.get("modelName") != self.hindi_model:
                raise MutationSafetyError("createModel may target only the Hindi note type")
        elif action in {"updateModelTemplates", "updateModelStyling"}:
            model = params.get("model", {})
            if model.get("name") != self.hindi_model:
                raise MutationSafetyError(f"{action} may target only the Hindi note type")
        elif action == "cloneDeckConfigId":
            if params.get("name") != self.hindi_preset:
                raise MutationSafetyError("options presets may be cloned only to the guarded Hindi name")
            # cloneFrom is intentionally permitted to reference the inherited preset read-only.
        elif action == "setDeckConfigId":
            if params.get("decks") != [self.hindi_deck]:
                raise MutationSafetyError("setDeckConfigId may target only the Hindi deck")
            config_id = int(params.get("configId", -1))
            if config_id in self.protected_config_ids or config_id not in self.hindi_config_ids:
                raise MutationSafetyError("setDeckConfigId attempted to use an unguarded or protected preset")
        elif action == "saveDeckConfig":
            config = params.get("config", {})
            config_id = int(config.get("id", -1))
            if config_id in self.protected_config_ids or config_id not in self.hindi_config_ids:
                raise MutationSafetyError("saveDeckConfig attempted to modify an unguarded or protected preset")
            if config.get("name") != self.hindi_preset:
                raise MutationSafetyError("saveDeckConfig attempted to rename or use the wrong Hindi preset")
        elif action in {"addNote", "addNotes"}:
            notes = [params.get("note", {})] if action == "addNote" else params.get("notes", [])
            for note in notes:
                if note.get("deckName") != self.hindi_deck or note.get("modelName") != self.hindi_model:
                    raise MutationSafetyError("notes may be added only to Hindi with Hindi Vocabulary")
        elif action == "updateNoteFields":
            self._guard_note_ids([int(params.get("note", {}).get("id", -1))])
        elif action in {"addTags", "removeTags"}:
            self._guard_note_ids([int(value) for value in params.get("notes", [])])
        elif action in {"reposition", "suspend", "unsuspend"}:
            self._guard_card_ids([int(value) for value in params.get("cards", [])])
        elif action == "setSpecificValueOfCard":
            self._guard_card_ids([int(params.get("card", -1))])
            if params.get("keys") != ["due"]:
                raise MutationSafetyError("Hindi due-order fallback may modify only the card due field")
        else:
            raise MutationSafetyError(f"mutation action {action!r} is not on the Hindi whitelist")


class AnkiClient:
    def __init__(
        self,
        *,
        url: str = ANKI_CONNECT_URL,
        transport: Transport | None = None,
        guard: MutationGuard | None = None,
    ) -> None:
        self.transport: Transport = transport or HttpTransport(url=url)
        self.guard = guard
        self.mutation_log: list[dict[str, Any]] = []

    def read(self, action: str, params: dict[str, Any] | None = None) -> Any:
        return self.transport(action, params)

    def mutate(self, action: str, params: dict[str, Any] | None = None) -> Any:
        if self.guard is None:
            raise MutationSafetyError("mutations require an installed MutationGuard")
        self.guard.validate(action, params)
        result = self.transport(action, params)
        self.mutation_log.append({"action": action, "params": params or {}, "result": result})
        return result
