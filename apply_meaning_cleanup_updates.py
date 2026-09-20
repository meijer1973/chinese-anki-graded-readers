from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
BACKUP_TSV = ROOT / "meaning_cleanup_before_update_backup.tsv"
APPLIED_TSV = ROOT / "meaning_cleanup_applied_updates.tsv"
REPORT_MD = ROOT / "meaning_cleanup_update_report.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_QUERY = "deck:Default"

TAIWAN_NOISE_RE = re.compile(
    r"\(Tw\)|\bTw\b|Taiwan pr\.|Taiwanese|Taiwan variant|southeast Taiwan",
    flags=re.IGNORECASE,
)

MEANING_OVERRIDES: dict[str, str] = {
    # Reviewed reading-character additions, 2026-09-20. Polyphonic senses were
    # checked against CC-CEDICT and https://www.zdic.net/hans/<character>.
    "叠": "to fold; to pile up; to overlap",
    "叹": "to sigh; to exclaim",
    "氓": "mang2: in 流氓, hooligan; rogue | meng2: common people (literary)",
    "蹭": "to rub against; to move slowly; to freeload (colloquial)",
    "瞪": "to stare; to glare; to open the eyes wide",
    "闺": "a woman's private room; relating to women (as in 闺蜜, close female friend)",
    "丫": "fork; branch; girl (in 丫头, colloquial)",
    "咧": "lie3: to part the lips; to grin | lie1: in 咧咧, jabber | lie5: dialectal final particle",
    "娇": "delicate; charming; pampered",
    "屈": "to bend; to yield; to feel wronged (in 委屈)",
    "槽": "trough; groove; channel; tank or sink (in 水槽)",
    "啪": "pop; bang; smack (sound)",
    "慨": "deeply moved; indignant; generous (in 慷慨)",
    "憋": "to hold back; to suppress; to hold one's breath",
    "抄": "to copy; to transcribe; to plagiarize",
    "啧": "to click one's tongue in admiration or disapproval",
    "嘻": "giggle; sound of laughter",
    "夕": "evening; dusk; sunset (in compounds)",
    "汪": "woof (dog's bark); expanse of water",
    "稚": "young; immature; childish (in 幼稚)",
    "皱": "to wrinkle; to crease; to frown (in 皱眉)",
    "兮": "literary exclamatory particle; descriptive suffix in expressions such as 可怜兮兮",
    "卦": "divinatory diagram; trigram; in 八卦, also gossip (colloquial)",
    "媳": "daughter-in-law (in 儿媳); wife (in 媳妇, colloquial)",
    "嫖": "to pay for sex; to visit a prostitute",
    "暑": "summer heat; hot weather",
    "柳": "willow",
    "樱": "cherry (in 樱花, cherry blossom; 樱桃, cherry fruit)",
    "讪": "to ridicule; embarrassed or sheepish (in 讪讪)",
    "凑": "to gather; to pool together; to move close to",
    "嘱": "to instruct; to urge; to tell someone to do something",
    "坑": "pit; hole; to cheat or rip off (colloquial)",
    "愁": "to worry; worry; sorrow",
    "扶": "to support with the hand; to help someone up; to assist",
    "拧": "ning2: to wring; to pinch | ning3: to twist; to screw | ning4: stubborn",
    "柱": "pillar; column; post",
    "柿": "persimmon",
    "畅": "smooth; unimpeded; free and easy (in compounds)",
    "瘸": "to limp; lame (of a leg)",
    "盼": "to hope for; to look forward to; to long for",
    "筷": "chopstick (usually 筷子)",
    "兼": "also; concurrently; to hold more than one role",
    "匆": "hurried; hasty (in 匆匆/匆忙)",
    "厘": "one hundredth; centi- (as in 厘米, centimeter)",
    "厮": "together; each other (in 厮守); fellow (derogatory); male servant (old)",
    "吭": "keng1: to utter a sound (in 吭声) | hang2: throat (literary)",
    "呲": "zi1: to bare the teeth (variant of 龇) | ci1: to scold (colloquial)",
    "呸": "pah!; bah!; to spit in contempt",
    "咆": "to roar (in 咆哮)",
    "咐": "to tell; to instruct (in 吩咐/嘱咐, where it is normally pronounced fu5)",
    "哗": "hua1: splashing or rustling sound | hua2: clamor; noisy talking",
    "哮": "to roar; to pant; to wheeze (in compounds)",
    "嗓": "throat; voice (usually 嗓子/嗓音)",
    "娼": "prostitute (formal or old usage)",
    "寒": "cold; chill; poor (literary)",
    "彤": "red; vermilion (in compounds)",
    "恍": "hazy; as if; suddenly (in 恍然, sudden realization)",
    "悟": "to realize; to understand; to comprehend",
    "悻": "resentful; disappointed or annoyed (in 悻悻)",
    "拽": "zhuai4: to pull; to drag | zhuai3: cocky | zhuai1: to throw (dialect) | ye4: variant of 曳, to drag",
    "摞": "to stack; a pile; a stack (also a measure word)",
    "斜": "slanting; tilted; diagonal",
    "歪": "wai1: crooked; askew; to tilt | wai3: to sprain (dialect)",
    "洒": "to spill; to sprinkle; to spray",
    "漆": "paint; lacquer; to paint",
    "癖": "strong habit; obsession; peculiar liking (in 癖好)",
    "秃": "bald; bare; barren",
    "耿": "upright; bright (literary); persistently troubled (in 耿耿于怀)",
    "脊": "spine; backbone; ridge (in compounds)",
    "腮": "cheek (especially the lower cheek)",
    "衷": "inner feelings; heartfelt; sincere (in 由衷/衷心)",
    "蹑": "to tiptoe; to tread softly; to follow",
    "阑": "late; waning; railing or screen (literary)",
    "阔": "wide; broad; spacious; wealthy",
    "鸽": "pigeon; dove",
    "伺": "ci4: to attend to; to serve (in 伺候) | si4: to watch; to wait for an opportunity",
    "侃": "to chat; to talk confidently; upright (literary)",
    # User-requested characters; 郝 intentionally keeps its useful surname sense.
    "郝": "Hao (Chinese family name)",
    "眯": "mi1: to squint; to doze | mi2: to get dust or grit in the eyes",
    "哄": "hong1: noisy laughter; hubbub | hong3: to coax; to soothe; to deceive | hong4: uproar; to make a commotion",
    "迅": "rapid; swift (in compounds such as 迅速)",
    "颠": "to jolt; to turn upside down; to topple; top or summit",
    "悠": "leisurely; long or distant; to swing or sway",
    "寝": "to sleep or rest; bedroom (in compounds such as 寝室)",
    "锅": "pot; pan; wok",
    # Reviewed single-character additions for the First Frost reading pilot.
    "瞬": "blink; instant (in 瞬间)",
    "愣": "be stunned; stare blankly; distracted",
    "抿": "press or close the lips lightly; sip; smooth down",
    "打": "da3: to hit; to call; to play; to do/make (verb-object phrases) | da2: dozen",
    "和": "he2: and; with | he4: to join in singing | huo4: to mix",
    "啊": "interjection; sentence-final particle for emphasis or response",
    "得": "de5: structural particle after a verb/adjective | de2: to get; to gain | dei3: must; need to",
    "哪": "which?; where?; sentence-final particle",
    "喔": "o1: oh; I see | wo1: rooster crow",
    "中": "zhong1: middle; in; China/Chinese | zhong4: to hit; to win",
    "差": "cha4: bad; lacking; different | cha1: difference; discrepancy | chai1: errand/job",
    "落": "luo4: to fall; to set | la4: to leave out; to fall behind | lao4: colloquial reading in compounds",
    "斗": "dou4: to fight; to struggle | dou3: dry measure; Big Dipper",
    "吧": "ba5: suggestion/surmise particle; ...right? | ba1: bar; to puff",
    "蒙": "meng1: to deceive; to guess blindly | meng2: misty; ignorant; to cover | Meng3: Mongol",
    "拜拜": "bye-bye; to say goodbye",
    "的": "de5: possessive/attributive particle | di2: truly | di4: target",
    "行": "xing2: okay; to walk/go | hang2: row; line; profession",
    "通": "to go through; to connect; to understand well",
    "乘": "cheng2: to ride; to make use of | sheng4: ancient chariot/measure",
    "厉害": "severe; intense; impressive; amazing",
    "成功": "to succeed; success; successful",
    "哦": "oh; I see; sentence-final particle",
    "老": "old; experienced; always; familiar prefix",
    "了": "le5: completed-action/change-of-state particle | liao3: to finish",
    "第": "prefix for ordinal numbers; rank/grade",
    "来": "to come; directional/result complement; ever since",
    "嗯": "mm; OK; yeah; interjection showing agreement",
    "嘛": "particle indicating obviousness or emphasis",
    "小子": "boy; kid; fellow (often derogatory)",
    "呢": "question/linking particle; ongoing-state particle",
    "么": "interrogative/final suffix, as in 什么/这么",
    "尸": "corpse; body; Kangxi radical 44",
    "虫": "insect; worm; bug; undesirable person",
    "高中": "senior high school; to pass an exam brilliantly",
    "呀": "ah; sentence-final particle after vowels",
    "啦": "sentence-final particle; sound of singing/cheering",
    "咱们": "we/us (including the listener)",
    "以为": "to think; to believe mistakenly",
    "一下": "a bit; a moment; used after verbs to soften tone",
    "克": "gram; to overcome; to restrain",
    "台": "platform; stage; desk; counter; Taiwan (abbr.)",
    "骑": "to ride (a horse, bike etc)",
    "出租车": "taxi",
    "追踪": "to track; to trace; to follow up",
    "艘": "classifier for ships",
    "骑士": "knight; rider",
    "哟": "yo1: oh! | yo5: sentence-final particle",
    "阿": "a1: familiar prefix before names/kinship terms | e1: to flatter",
    "罢了": "that's all; nothing more; don't mind it",
    "出局": "to be put out/eliminated; out of the game",
    "剂": "compound/medicinal preparation; dose; measure word for medicine",
    "枚": "classifier for small flat objects",
    "喽": "final particle like 了; mild warning/attention particle",
    "丑": "ugly; shameful; clown; second Earthly Branch",
    "巴": "to long for; to cling to; Ba/Sichuan-Chongqing region",
    "配合": "to coordinate; to cooperate; to work together",
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\t", " ")).strip()


def anki(action: str, params: dict[str, Any] | None = None) -> Any:
    payload = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params

    request = Request(
        ANKI_CONNECT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


def note_field(note: dict[str, Any], name: str) -> str:
    return clean(note.get("fields", {}).get(name, {}).get("value", ""))


def load_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def issue_list(meaning: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"\bsurname\b", meaning, flags=re.IGNORECASE):
        issues.append("surname_noise")
    if TAIWAN_NOISE_RE.search(meaning):
        issues.append("taiwan_noise")
    if len(meaning) >= 180:
        issues.append("very_long")
    elif len(meaning) >= 130:
        issues.append("long")
    if len(meaning) >= 255:
        issues.append("likely_truncated")
    if meaning.count(";") >= 6:
        issues.append("too_many_senses")
    return issues


def split_group(group: str) -> tuple[str, str]:
    match = re.match(r"^([^:|]{1,40}):\s*(.*)$", group.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", group.strip()


def should_drop_taiwan_part(word: str, part: str) -> bool:
    lowered = part.lower().strip()
    if lowered.startswith("(tw)") or lowered.startswith("tw "):
        return True
    if lowered.startswith("(hk, tw)") or lowered.startswith("(tw, hk)"):
        return True
    if "taiwan variant" in lowered or "southeast taiwan" in lowered:
        return True
    if "taiwan" in lowered and word not in {"台", "台湾", "臺灣"}:
        return True
    return False


def tidy_part(word: str, part: str) -> str:
    value = clean(part)
    if not value:
        return ""
    if re.search(r"\bsurname\b", value, flags=re.IGNORECASE):
        return ""
    if should_drop_taiwan_part(word, value):
        return ""

    value = re.sub(r"\s*\(Taiwan pr\. \[[^\]]+\]\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bTaiwan pr\. \[[^\]]+\]", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\((?:e\.g\.|for example)[^)]*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\(as in [^)]*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\(Note: [^)]*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\(CL:[^)]*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bCL:[^;]+", "", value, flags=re.IGNORECASE)
    value = clean(value).strip(" ;")

    if not value or should_drop_taiwan_part(word, value):
        return ""
    return value


def shorten_part(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value

    cut_points = []
    for separator in (", ", " (", " or ", " and "):
        index = value.rfind(separator, 0, limit)
        if index >= 35:
            cut_points.append(index)

    if cut_points:
        return value[: max(cut_points)].rstrip(" ,;")
    return value[:limit].rstrip(" ,;")


def cleaned_meaning(word: str, meaning: str) -> str:
    if word in MEANING_OVERRIDES:
        return MEANING_OVERRIDES[word]

    issues = issue_list(meaning)
    if not issues:
        return meaning

    raw_groups = [group.strip() for group in meaning.split(" | ") if group.strip()]
    multi_group = len(raw_groups) > 1
    cleaned_groups: list[str] = []

    for raw_group in raw_groups:
        label, body = split_group(raw_group)
        parts: list[str] = []
        for raw_part in body.split(";"):
            part = tidy_part(word, raw_part)
            if part and part not in parts:
                parts.append(part)

        if not parts:
            continue

        if len(raw_groups) >= 4:
            max_parts = 1
        elif multi_group or len(meaning) >= 180:
            max_parts = 2
        elif len(meaning) >= 130 or meaning.count(";") >= 6:
            max_parts = 3
        else:
            max_parts = len(parts)

        part_limit = 80 if multi_group else 95
        text = "; ".join(shorten_part(part, part_limit) for part in parts[:max_parts])
        cleaned_groups.append(f"{label}: {text}" if label else text)

    return clean(" | ".join(cleaned_groups) if cleaned_groups else meaning)


def write_backup(notes: list[dict[str, Any]]) -> None:
    fieldnames = ["Note ID", "Word", "Pinyin", "Old Meaning", "Frequency Rank"]
    rows = [
        {
            "Note ID": str(note["noteId"]),
            "Word": note_field(note, "Word"),
            "Pinyin": note_field(note, "Pinyin"),
            "Old Meaning": note_field(note, "Meaning"),
            "Frequency Rank": note_field(note, "Frequency Rank"),
        }
        for note in notes
    ]
    with BACKUP_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def apply_updates(notes: list[dict[str, Any]]) -> dict[str, Any]:
    fieldnames = [
        "Note ID",
        "Word",
        "Pinyin",
        "Issues",
        "Old Meaning",
        "New Meaning",
        "Old Length",
        "New Length",
    ]
    applied_rows: list[dict[str, str]] = []
    actions: list[dict[str, Any]] = []
    issue_counts: Counter[str] = Counter()

    for note in notes:
        word = note_field(note, "Word")
        old_meaning = note_field(note, "Meaning")
        new_meaning = cleaned_meaning(word, old_meaning)
        if new_meaning == old_meaning:
            continue

        issues = issue_list(old_meaning)
        if word in MEANING_OVERRIDES and "manual_override" not in issues:
            issues.append("manual_override")
        for issue in issues:
            issue_counts[issue] += 1

        applied_rows.append(
            {
                "Note ID": str(note["noteId"]),
                "Word": word,
                "Pinyin": note_field(note, "Pinyin"),
                "Issues": ", ".join(issues),
                "Old Meaning": old_meaning,
                "New Meaning": new_meaning,
                "Old Length": str(len(old_meaning)),
                "New Length": str(len(new_meaning)),
            }
        )
        actions.append(
            {
                "action": "updateNoteFields",
                "params": {"note": {"id": int(note["noteId"]), "fields": {"Meaning": new_meaning}}},
            }
        )

    with APPLIED_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(applied_rows)

    for start in range(0, len(actions), 50):
        results = anki("multi", {"actions": actions[start : start + 50]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])

    return {
        "notes_updated": len(actions),
        "issue_counts": dict(sorted(issue_counts.items())),
        "changed_preview": [row["Word"] for row in applied_rows[:20]],
    }


def collection_stats(notes: list[dict[str, Any]]) -> dict[str, int]:
    meanings = [note_field(note, "Meaning") for note in notes]
    return {
        "surname_noise": sum(1 for meaning in meanings if re.search(r"\bsurname\b", meaning, flags=re.IGNORECASE)),
        "taiwan_noise": sum(1 for meaning in meanings if TAIWAN_NOISE_RE.search(meaning)),
        "long": sum(1 for meaning in meanings if len(meaning) >= 130),
        "very_long": sum(1 for meaning in meanings if len(meaning) >= 180),
        "too_many_senses": sum(1 for meaning in meanings if meaning.count(";") >= 6),
    }


def write_report(before: dict[str, int], result: dict[str, Any], after: dict[str, int]) -> None:
    lines = [
        "# Meaning Cleanup Update Report",
        "",
        f"Notes updated: {result['notes_updated']}",
        "",
        "Before:",
        f"- surname noise: {before['surname_noise']}",
        f"- Taiwan-specific noise: {before['taiwan_noise']}",
        f"- meanings >= 130 chars: {before['long']}",
        f"- meanings >= 180 chars: {before['very_long']}",
        f"- meanings with >= 6 semicolons: {before['too_many_senses']}",
        "",
        "After:",
        f"- surname noise: {after['surname_noise']}",
        f"- Taiwan-specific noise: {after['taiwan_noise']}",
        f"- meanings >= 130 chars: {after['long']}",
        f"- meanings >= 180 chars: {after['very_long']}",
        f"- meanings with >= 6 semicolons: {after['too_many_senses']}",
        "",
        "Applied issue counts:",
    ]
    for issue, count in result["issue_counts"].items():
        lines.append(f"- {issue}: {count}")
    lines.extend(
        [
            "",
            "Files:",
            f"- {BACKUP_TSV.name}: previous meaning fields before update",
            f"- {APPLIED_TSV.name}: meaning changes applied in this cleanup",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    before_notes = load_notes()
    before = collection_stats(before_notes)
    write_backup(before_notes)
    result = apply_updates(before_notes)
    after = collection_stats(load_notes())
    write_report(before, result, after)
    print(json.dumps({**result, "before": before, "after": after}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
