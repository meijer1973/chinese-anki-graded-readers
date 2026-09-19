from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
ANKI_CONNECT_VERSION = 6


class AnkiConnectError(RuntimeError):
    """Raised when AnkiConnect is unavailable or rejects a request."""


class MutationSafetyError(RuntimeError):
    """Raised before a mutation crosses the China Knowledge boundary."""


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
    target_deck: str
    target_model: str
    target_preset: str
    protected_note_ids: set[int] = field(default_factory=set)
    protected_card_ids: set[int] = field(default_factory=set)
    protected_config_ids: set[int] = field(default_factory=set)
    target_note_ids: set[int] = field(default_factory=set)
    target_config_ids: set[int] = field(default_factory=set)

    def register_target_notes(self, values: list[int] | set[int]) -> None:
        note_ids = {int(value) for value in values}
        if note_ids & self.protected_note_ids:
            raise MutationSafetyError("a target note ID is also protected")
        self.target_note_ids.update(note_ids)

    def register_target_config(self, value: int) -> None:
        config_id = int(value)
        if config_id in self.protected_config_ids:
            raise MutationSafetyError(f"configuration ID {config_id} is protected")
        self.target_config_ids.add(config_id)

    def _guard_note_ids(self, values: list[int]) -> None:
        note_ids = {int(value) for value in values}
        protected = note_ids & self.protected_note_ids
        if protected:
            raise MutationSafetyError(
                f"attempted mutation of protected note IDs: {sorted(protected)[:10]}"
            )
        unknown = note_ids - self.target_note_ids
        if unknown:
            raise MutationSafetyError(
                f"attempted mutation of unregistered note IDs: {sorted(unknown)[:10]}"
            )

    def validate(self, action: str, params: dict[str, Any] | None) -> None:
        params = params or {}
        if action == "createDeck":
            if params.get("deck") != self.target_deck:
                raise MutationSafetyError("createDeck may target only the guarded deck")
        elif action == "createModel":
            if params.get("modelName") != self.target_model:
                raise MutationSafetyError("createModel may target only the guarded note type")
        elif action in {"updateModelTemplates", "updateModelStyling"}:
            if params.get("model", {}).get("name") != self.target_model:
                raise MutationSafetyError(f"{action} may target only the guarded note type")
        elif action == "cloneDeckConfigId":
            if params.get("name") != self.target_preset:
                raise MutationSafetyError("options presets may be cloned only to the guarded name")
        elif action == "setDeckConfigId":
            if params.get("decks") != [self.target_deck]:
                raise MutationSafetyError("setDeckConfigId may target only China Knowledge")
            config_id = int(params.get("configId", -1))
            if config_id in self.protected_config_ids or config_id not in self.target_config_ids:
                raise MutationSafetyError("attempted to assign an unguarded or protected preset")
        elif action == "saveDeckConfig":
            config = params.get("config", {})
            config_id = int(config.get("id", -1))
            if config_id in self.protected_config_ids or config_id not in self.target_config_ids:
                raise MutationSafetyError("attempted to modify an unguarded or protected preset")
            if config.get("name") != self.target_preset:
                raise MutationSafetyError("attempted to rename the guarded preset")
        elif action in {"addNote", "addNotes"}:
            notes = [params.get("note", {})] if action == "addNote" else params.get("notes", [])
            for note in notes:
                if note.get("deckName") != self.target_deck or note.get("modelName") != self.target_model:
                    raise MutationSafetyError("notes may be added only to the guarded deck and model")
        elif action == "updateNoteFields":
            self._guard_note_ids([int(params.get("note", {}).get("id", -1))])
        elif action in {"addTags", "removeTags"}:
            self._guard_note_ids([int(value) for value in params.get("notes", [])])
        else:
            raise MutationSafetyError(
                f"mutation action {action!r} is not on the China Knowledge whitelist"
            )


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
