"""Run inside Anki's documented Debug Console; all mutations use native APIs.

No live SQL writes, rescheduling, optimization, answers, note creation, or syncing.
See docs/chinese-subdecks-fsrs.md for backup/restore gates and invocation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.chinese_card_categories import classify, in_deck_scope

TABLES = ("cards", "notes", "revlog", "fields", "templates", "notetypes", "tags", "graves")
TARGETS = {
    "single": ("Single characters", 95),
    "sentence": ("Sentences", 80),
    "multi": ("Multi-character words", 90),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def json_value(value):
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    return value


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_table(all_rows, name):
    # Fixed internal table names only. These are read-only queries.
    schema = all_rows(f"pragma table_info({name})")
    columns = [r[1] for r in schema]
    # Anki's Rust DB bridge returns blobs as lists of bytes; sqlite3 returns
    # bytes. Normalize by declared column type, not by guessing arbitrary lists.
    blob_columns = {i for i, column in enumerate(schema) if column[2].upper() == "BLOB"}
    rows = [[bytes(v) if i in blob_columns and isinstance(v, list) else v
             for i, v in enumerate(row)] for row in all_rows(f"select * from {name}")]
    rows.sort(key=lambda row: json.dumps(json_value(row[:2]), ensure_ascii=False))
    return {"columns": columns, "rows": json_value(rows)}


def media_hashes(folder):
    folder = Path(folder)
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def capture(col):
    return {
        "collection_path": str(col.path),
        "tables": {name: read_table(col.db.all, name) for name in TABLES},
        "decks": sorted(col.decks.all(), key=lambda d: d["id"]),
        "presets": sorted(col.decks.all_config(), key=lambda d: d["id"]),
        "models": sorted(col.models.all(), key=lambda d: d["id"]),
        "media": media_hashes(col.media.dir()),
        "global_options": {k: json_value(v) for k, v in col.db.all("select key, val from config")
                           if k in {"fsrs", "fsrsHealthCheck", "fsrsShortTermWithStepsEnabled", "schedVer",
                                    "newCardsIgnoreReviewLimit", "applyAllParentLimits"}},
    }


def table_dicts(snapshot, name):
    table = snapshot["tables"][name]
    return [dict(zip(table["columns"], row)) for row in table["rows"]]


def make_plan(snapshot, parent="Default"):
    decks = {d["id"]: d for d in snapshot["decks"]}
    parents = [d for d in decks.values() if d["name"] == parent]
    require(len(parents) == 1 and not parents[0]["dyn"], "Parent must be one existing normal deck")
    base = parents[0]
    models = {m["id"]: m for m in snapshot["models"]}
    notes = {n["id"]: n for n in table_dicts(snapshot, "notes")}
    rows = []
    for card in table_dicts(snapshot, "cards"):
        home = decks.get(card["odid"] or card["did"])
        if not home or not in_deck_scope(home["name"], parent):
            continue
        note = notes[card["nid"]]
        model = models[note["mid"]]
        fields = dict(zip([f["name"] for f in model["flds"]], note["flds"].split("\x1f")))
        templates = [t for t in model["tmpls"] if t["ord"] == card["ord"]]
        category, reason = classify(model["name"], templates[0] if len(templates) == 1 else {}, fields)
        destination = decks[card["did"]]["name"]
        if card["odid"]:
            category, reason = "ambiguous", "Filtered membership: leave in place for explicit review"
        elif home.get("conf") != base["conf"]:
            category, reason = "ambiguous", "Different source preset: needs a preservation-aware nested destination"
        elif category in TARGETS:
            destination = parent + "::" + TARGETS[category][0]
        rows.append({"card_id": card["id"], "note_id": card["nid"], "word": fields.get("Word", ""),
                     "original_deck_id": card["did"], "original_deck": decks[card["did"]]["name"],
                     "destination": destination, "category": category, "reason": reason,
                     "suspended": card["queue"] == -1, "buried": card["queue"] in {-2, -3},
                     "move": destination != decks[card["did"]]["name"]})
    return {"parent": parent, "parent_deck": base, "rows": rows,
            "counts": dict(Counter(r["category"] for r in rows)),
            "moves": dict(Counter(r["category"] for r in rows if r["move"])),
            "suspended": dict(Counter(r["category"] for r in rows if r["suspended"])),
            "buried": sum(r["buried"] for r in rows),
            "unresolved": [r for r in rows if r["category"] == "ambiguous"]}


def verify_restore(col, *, profile_name, sync_configured, backup, backup_database, out):
    require(profile_name.startswith("Subdeck restore test ") and not sync_configured,
            "Restore verification must run in an isolated profile without sync credentials")
    before = capture(col)
    save(Path(out).with_name("restored-snapshot.json"), before)
    source = sqlite3.connect(Path(backup_database).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    source.create_collation("unicase", lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()))
    try:
        tables = TABLES + ("decks", "deck_config")
        for name in tables:
            expected = read_table(lambda sql: source.execute(sql).fetchall(), name)
            actual = read_table(col.db.all, name)
            require(expected == actual, f"Restored {name} differs from collection backup")
    finally:
        source.close()
    # This installation's media-inclusive package has an empty media manifest.
    # Callers with nonempty media must supply and validate a full media manifest.
    require(before["media"] == {}, "Nonempty media requires explicit backup media comparison")
    restored = {
        "status": "PASS", "profile": profile_name, "sync_configured": False,
        "backup": str(Path(backup).resolve()), "backup_sha256": file_hash(backup),
        "backup_size": Path(backup).stat().st_size, "backup_database_sha256": file_hash(backup_database),
        "snapshot": before, "verified_tables": list(tables), "media_files_verified": 0,
    }
    save(out, restored)
    return {k: v for k, v in restored.items() if k != "snapshot"}


def verify_change(before, after, plan, destination_ids, *, mix_new=False):
    expected = {r["card_id"]: destination_ids[r["destination"]] for r in plan["rows"] if r["move"]}
    old_cards = {c["id"]: c for c in table_dicts(before, "cards")}
    new_cards = {c["id"]: c for c in table_dicts(after, "cards")}
    require(old_cards.keys() == new_cards.keys(), "Card IDs changed")
    for cid, original in old_cards.items():
        current = new_cards[cid]
        allowed = {"did", "mod", "usn"} if cid in expected else set()
        require({k: v for k, v in original.items() if k not in allowed}
                == {k: v for k, v in current.items() if k not in allowed}, f"Card state changed: {cid}")
        require(current["did"] == expected.get(cid, original["did"]), f"Wrong destination: {cid}")
    for name in TABLES:
        if name != "cards":
            require(before["tables"][name] == after["tables"][name], f"Unexpected {name} change")
    for key in ("models", "media", "global_options"):
        require(before[key] == after[key], f"Unexpected {key} change")
    parent = plan["parent_deck"]
    old_presets = {p["id"]: p for p in before["presets"]}
    new_presets = {p["id"]: p for p in after["presets"]}
    require(old_presets.keys() == new_presets.keys(), "Preset IDs changed")
    for pid, old in old_presets.items():
        desired = copy.deepcopy(old)
        allowed = set()
        if mix_new and pid == parent["conf"]:
            desired["newGatherPriority"] = 1
            allowed = {"mod", "usn"}
        require({k: v for k, v in desired.items() if k not in allowed}
                == {k: v for k, v in new_presets[pid].items() if k not in allowed}, f"Preset changed: {pid}")
    after_decks = {d["id"]: d for d in after["decks"]}
    original_ids = {d["id"] for d in before["decks"]}
    intended_names = {plan["parent"] + "::" + suffix for suffix, _ in TARGETS.values()}
    for deck in after["decks"]:
        if deck["id"] not in original_ids:
            require(deck["name"] in intended_names, "Unexpected new deck")
            require(deck["conf"] == parent["conf"] and not deck["dyn"], "Wrong new deck preset/type")
            for key in ("newLimit", "reviewLimit", "newLimitToday", "reviewLimitToday"):
                require(deck.get(key) == parent.get(key), f"New deck limit differs: {key}")
    for old in before["decks"]:
        current = after_decks[old["id"]]
        # Existing category decks may only acquire their requested retention.
        target = next((percent for suffix, percent in TARGETS.values()
                       if old["name"] == plan["parent"] + "::" + suffix), None)
        desired = {**old, "desiredRetention": target} if target is not None else old
        allowed = {"mod", "usn"} if target is not None else set()
        require({k: v for k, v in desired.items() if k not in allowed}
                == {k: v for k, v in current.items() if k not in allowed}, f"Existing deck changed: {old['name']}")


def migrate(col, *, profile_name, backup_verification, out_dir, apply=False, mix_new=False):
    before = capture(col)
    plan = make_plan(before)
    parent = plan["parent_deck"]
    options = col.decks.get_deck_configs_for_update(parent["id"])
    require(options.fsrs, "FSRS must already be enabled")
    require(not any(t.get("did") for m in before["models"] if m["name"] == "Chinese Vocabulary" for t in m["tmpls"]),
            "Existing template deck overrides require review before routing future imports")
    if mix_new:
        require(all(d.get("conf") != parent["conf"] for d in before["decks"]
                    if not in_deck_scope(d["name"], plan["parent"])), "Parent preset is shared outside the Chinese scope")
    for category, (suffix, _) in TARGETS.items():
        if plan["counts"].get(category):
            existing = next((d for d in before["decks"] if d["name"] == plan["parent"] + "::" + suffix), None)
            require(existing is None or (not existing["dyn"] and existing.get("conf") == parent["conf"]),
                    f"Destination preset/type conflict: {suffix}; review before any mutation")
    folder = Path(out_dir)
    save(folder / "dry_run.json", plan)
    if not apply:
        save(folder / "dry_run_snapshot.json", before)
        return {k: v for k, v in plan.items() if k not in {"rows", "parent_deck"}}
    evidence = json.loads(Path(backup_verification).read_text(encoding="utf-8"))
    require(evidence["status"] == "PASS" and not evidence["sync_configured"], "Backup restoration has not passed")
    require(file_hash(evidence["backup"]) == evidence["backup_sha256"], "Verified backup changed")
    option_changes = any(
        next((d.get("desiredRetention") for d in before["decks"]
              if d["name"] == plan["parent"] + "::" + suffix), None) != percent
        for category, (suffix, percent) in TARGETS.items() if plan["counts"].get(category)
    ) or (mix_new and next(p for p in before["presets"] if p["id"] == parent["conf"]).get("newGatherPriority") != 1)
    if plan["moves"] or option_changes:
        # Refuse stale full backups before any mutation. No-op reruns do not use
        # historical schedules as a preservation baseline or reject study progress.
        for key in ("tables", "decks", "presets", "models", "media", "global_options"):
            require(json_value(before[key]) == evidence["snapshot"][key],
                    f"Backup no longer matches current {key}; make and restore-test a fresh backup")
    require(not (folder / "before.json").exists(), "Use a fresh output directory; never overwrite an earlier run")
    # Fresh preservation baseline on every run. Historical installation snapshots
    # are never used to reject normal subsequent learning progress.
    save(folder / "before.json", before)
    save(folder / "rollback_manifest.json", {"backup": evidence["backup"], "profile": profile_name, "plan": plan,
                                            "created_at_utc": datetime.now(timezone.utc).isoformat()})
    dest_ids = {d["name"]: d["id"] for d in before["decks"]}
    for category, (suffix, percent) in TARGETS.items():
        if not plan["counts"].get(category):
            continue
        name = plan["parent"] + "::" + suffix
        did = col.decks.add_normal_deck_with_name(name).id
        deck = col.decks.get(did)
        if name not in dest_ids:
            deck["conf"] = parent["conf"]
            for key in ("newLimit", "reviewLimit", "newLimitToday", "reviewLimitToday"):
                deck[key] = copy.deepcopy(parent.get(key))
        require(deck["conf"] == parent["conf"], f"Destination preset conflict: {name}")
        if deck.get("desiredRetention") != percent or name not in dest_ids:
            deck["desiredRetention"] = percent  # legacy deck dictionaries use integer percentages
            col.decks.update_dict(deck)  # no fsrs_reschedule or memory-state recomputation
        dest_ids[name] = did
    moved = [r for r in plan["rows"] if r["move"]]
    for start in range(0, len(moved), 250):
        changed = []
        for row in moved[start:start + 250]:
            card = col.get_card(row["card_id"])
            require(card.did == row["original_deck_id"] and not card.odid, "Card moved since the dry run")
            card.did = dest_ids[row["destination"]]
            changed.append(card)
        # set_deck() in Anki 26.09.2 recomputes FSRS memory state. Updating just
        # did through the native Card API preserves all existing memory data.
        col.update_cards(changed)
    if mix_new:
        config = col.decks.get_config(parent["conf"])
        if config.get("newGatherPriority") != 1:
            config["newGatherPriority"] = 1
            col.decks.update_config(config)
    after = capture(col)
    verify_change(before, after, plan, dest_ids, mix_new=mix_new)
    for suffix, percent in TARGETS.values():
        did = dest_ids.get(plan["parent"] + "::" + suffix)
        if did:
            current = col.decks.get_deck_configs_for_update(did)
            require(abs(current.current_deck.limits.desired_retention - percent / 100) < 0.00001,
                    f"Effective retention mismatch: {suffix}")
    repeat = make_plan(after)
    require(not repeat["moves"], "Repeat execution would move cards again")
    report = {"status": "PASS", "counts": plan["counts"], "moved": plan["moves"],
              "suspended": plan["suspended"], "buried": plan["buried"], "unresolved": plan["unresolved"],
              "note_count": len(table_dicts(after, "notes")), "card_count": len(table_dicts(after, "cards")),
              "review_log_count": len(table_dicts(after, "revlog")), "memory_state_and_schedules_preserved": True,
              "backup": evidence["backup"], "preserved_mixed_new_order": mix_new, "repeat_moves": 0}
    save(folder / "after.json", after)
    save(folder / "verification.json", report)
    return report
