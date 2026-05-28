from __future__ import annotations

import csv
import html
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

try:
    from novel_tools import (
        DEFAULT_KNOWN_WORDS,
        DEFAULT_PUNCTUATION,
        HANZI_RE,
        LAYER_TOKEN_FIELDS,
        load_layered_vocabulary,
        load_punctuation,
        normalize_token,
        utc_now,
        write_json,
    )
except ModuleNotFoundError:
    from scripts.novel_tools import (
        DEFAULT_KNOWN_WORDS,
        DEFAULT_PUNCTUATION,
        HANZI_RE,
        LAYER_TOKEN_FIELDS,
        load_layered_vocabulary,
        load_punctuation,
        normalize_token,
        utc_now,
        write_json,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTATIONS_DIR = ROOT / "adaptations"
RIGHTS_STATUSES = {"public_domain", "licensed", "own_text", "private_study", "unclear"}
SOURCE_SKIP_NAME_RE = re.compile(r"(nav|toc|cover|copyright|contents?|title[-_ ]?page|ads?)", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?]+")


class BodyTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_body = False
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "body":
            self.in_body = True
        if tag in {"script", "style", "nav"}:
            self.skip_depth += 1
        if self.in_body and tag in {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "nav"} and self.skip_depth:
            self.skip_depth -= 1
        if self.in_body and tag in {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li"}:
            self.parts.append("\n")
        if tag == "body":
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self.in_body and not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return clean_text("".join(self.parts))


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_first(element: ET.Element, local_name: str) -> ET.Element | None:
    for child in element.iter():
        if strip_namespace(child.tag) == local_name:
            return child
    return None


def spine_items(epub_path: str | Path) -> list[dict]:
    epub = Path(epub_path)
    with zipfile.ZipFile(epub) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = find_first(container, "rootfile")
        if rootfile is None:
            raise ValueError("EPUB container.xml does not declare a rootfile.")
        opf_name = rootfile.attrib["full-path"]
        opf_root = ET.fromstring(zf.read(opf_name))
        opf_dir = Path(opf_name).parent
        manifest: dict[str, dict] = {}
        for item in opf_root.iter():
            if strip_namespace(item.tag) != "item":
                continue
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if not item_id or not href:
                continue
            manifest[item_id] = {
                "id": item_id,
                "href": href,
                "media_type": item.attrib.get("media-type", ""),
                "properties": item.attrib.get("properties", ""),
                "zip_path": str((opf_dir / unquote(href)).as_posix()).lstrip("./"),
            }

        ordered = []
        for itemref in opf_root.iter():
            if strip_namespace(itemref.tag) != "itemref":
                continue
            idref = itemref.attrib.get("idref")
            if idref and idref in manifest:
                ordered.append(manifest[idref])
        return ordered


def should_skip_spine_item(item: dict) -> bool:
    path = item.get("zip_path", "")
    media_type = item.get("media_type", "")
    properties = item.get("properties", "")
    if "nav" in properties.split():
        return True
    if "xhtml" not in media_type and "html" not in media_type:
        return True
    return bool(SOURCE_SKIP_NAME_RE.search(path))


def extract_epub_text_items(epub_path: str | Path) -> list[dict]:
    items = []
    with zipfile.ZipFile(epub_path) as zf:
        for index, item in enumerate(spine_items(epub_path), start=1):
            skipped = should_skip_spine_item(item)
            text = ""
            if not skipped:
                try:
                    raw = zf.read(item["zip_path"]).decode("utf-8", errors="replace")
                except KeyError:
                    skipped = True
                else:
                    extractor = BodyTextExtractor()
                    extractor.feed(raw)
                    text = extractor.text()
                    if not text:
                        skipped = True
            items.append(
                {
                    "spine_index": index,
                    "zip_path": item.get("zip_path", ""),
                    "href": item.get("href", ""),
                    "skipped": skipped,
                    "text": text,
                    "rough_token_count": rough_token_count(text),
                }
            )
    return items


def rough_token_count(text: str) -> int:
    hanzi = len(HANZI_RE.findall(text))
    latin_or_digit = len(re.findall(r"[A-Za-z0-9]+", text))
    return hanzi + latin_or_digit


def split_text_into_units(text_items: list[dict], *, min_unit_tokens: int = 800, max_unit_tokens: int = 1500) -> list[dict]:
    units: list[dict] = []
    current_paragraphs: list[str] = []
    current_sources: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current_paragraphs, current_sources, current_tokens
        if not current_paragraphs:
            return
        unit_id = f"unit_{len(units) + 1:03d}"
        text = "\n\n".join(current_paragraphs).strip()
        units.append(
            {
                "unit_id": unit_id,
                "text": text,
                "source_items": sorted(set(current_sources)),
                "rough_token_count": rough_token_count(text),
                "paragraph_count": len(current_paragraphs),
            }
        )
        current_paragraphs = []
        current_sources = []
        current_tokens = 0

    for item in text_items:
        if item.get("skipped") or not item.get("text"):
            continue
        paragraphs = [line.strip() for line in item["text"].splitlines() if line.strip()]
        for paragraph in paragraphs:
            paragraph_tokens = rough_token_count(paragraph)
            if current_paragraphs and current_tokens >= min_unit_tokens and current_tokens + paragraph_tokens > max_unit_tokens:
                flush()
            current_paragraphs.append(paragraph)
            current_sources.append(item["zip_path"])
            current_tokens += paragraph_tokens
            if current_tokens >= max_unit_tokens:
                flush()
    flush()
    return units


def write_empty_tsv(path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()


def import_epub_for_adaptation(
    epub_path: str | Path,
    slug: str,
    *,
    adaptations_dir: str | Path = DEFAULT_ADAPTATIONS_DIR,
    rights_status: str = "unclear",
    min_unit_tokens: int = 800,
    max_unit_tokens: int = 1500,
    copy_source_private: bool = False,
    force: bool = False,
) -> dict:
    if rights_status not in RIGHTS_STATUSES:
        raise ValueError(f"rights_status must be one of {sorted(RIGHTS_STATUSES)}")
    epub = Path(epub_path)
    if not epub.exists():
        raise FileNotFoundError(epub)
    root = Path(adaptations_dir) / slug
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"{root} already exists. Pass --force to overwrite generated intake files.")
    root.mkdir(parents=True, exist_ok=True)
    source_units_dir = root / "source_units"
    source_units_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for old_unit in source_units_dir.glob("unit_*_source.md"):
            old_unit.unlink()

    private_dir = root / "source_private"
    private_dir.mkdir(parents=True, exist_ok=True)
    copied_source = None
    if copy_source_private:
        copied_source = private_dir / epub.name
        shutil.copy2(epub, copied_source)

    text_items = extract_epub_text_items(epub)
    units = split_text_into_units(text_items, min_unit_tokens=min_unit_tokens, max_unit_tokens=max_unit_tokens)
    unit_entries = []
    for unit in units:
        unit_path = source_units_dir / f"{unit['unit_id']}_source.md"
        unit_path.write_text(unit["text"].rstrip() + "\n", encoding="utf-8")
        unit_entries.append(
            {
                "unit_id": unit["unit_id"],
                "unit_path": str(unit_path),
                "source_items": unit["source_items"],
                "rough_token_count": unit["rough_token_count"],
                "paragraph_count": unit["paragraph_count"],
            }
        )

    source_map = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "slug": slug,
        "epub_filename": epub.name,
        "rights_status": rights_status,
        "source_private_policy": "Raw EPUB and extracted full source are private/local by default. Do not track copyrighted source.",
        "copied_source_private_path": str(copied_source) if copied_source else None,
        "spine_item_count": len(text_items),
        "skipped_spine_items": [item for item in text_items if item["skipped"]],
        "source_unit_count": len(unit_entries),
        "source_units": unit_entries,
    }
    write_json(root / "source_map.json", source_map)
    config = {
        "schema_version": 1,
        "slug": slug,
        "rights_status": rights_status,
        "target_readable_coverage_percent": 98,
        "preferred_forbidden_unknown_tokens_per_chapter": 0,
        "maximum_forbidden_unknown_tokens_per_chapter": 5,
        "minimal_intervention_cascade": [
            "classify proper nouns and personal-known words",
            "approve high-value stretch or book-specific words",
            "replace hard word with easy known synonym",
            "simplify phrase",
            "split or simplify sentence",
            "rewrite paragraph while preserving source facts",
            "condense or summarize only when required",
        ],
    }
    write_json(root / "adaptation_config.json", config)
    (root / "adaptation_plan.md").write_text(
        f"""# Adaptation Plan: {slug}

Rights status: {rights_status}

## Rule

Diagnose first, classify vocabulary second, rewrite last. Do not create tracked derivative text from copyrighted source unless rights allow it.

## Next Steps

1. Run `scripts/profile_adaptation_vocabulary.py`.
2. Review `proper_noun_candidates.tsv`.
3. Review `stretch_candidates.tsv`.
4. Create the normal `manuscripts/<adapted-slug>/` project only after source rights and vocabulary policy are clear.
5. Keep `adaptation_log.md` with source-unit IDs, intervention level, changes, and rationale.
""",
        encoding="utf-8",
    )
    write_empty_tsv(root / "proper_noun_candidates.tsv", ["candidate", "candidate_class", "frequency", "source_units", "status", "notes"])
    write_empty_tsv(
        root / "stretch_candidates.tsv",
        [
            "word",
            "pinyin",
            "rough_meaning",
            "frequency",
            "dispersion",
            "source_units",
            "proposed_layer",
            "reason",
            "replacement_feasibility",
            "status",
        ],
    )
    return source_map


def source_unit_files(source_units_dir: str | Path) -> list[Path]:
    files = sorted(Path(source_units_dir).glob("unit_*_source.md"))
    if not files:
        raise ValueError(f"No source unit files found in {source_units_dir}")
    return files


def tokenize_source_text(text: str, vocabulary_tokens: set[str] | None = None, punctuation: set[str] | None = None) -> list[str]:
    punctuation = punctuation or load_punctuation()
    vocabulary_tokens = vocabulary_tokens or set()
    max_token_len = max((len(token) for token in vocabulary_tokens), default=1)
    if re.search(r"\s", text):
        tokens = []
        for raw in text.split():
            token = normalize_token(raw, punctuation)
            if token:
                tokens.append(token)
        return tokens

    tokens = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in punctuation or char.isspace():
            index += 1
            continue
        matched = None
        if HANZI_RE.match(char):
            upper = min(len(text), index + max_token_len)
            for end in range(upper, index, -1):
                candidate = text[index:end]
                if candidate in vocabulary_tokens:
                    matched = candidate
                    break
            if matched:
                tokens.append(matched)
                index += len(matched)
            else:
                tokens.append(char)
                index += 1
            continue
        match = re.match(r"[A-Za-z0-9]+", text[index:])
        if match:
            tokens.append(match.group(0))
            index += len(match.group(0))
        else:
            index += 1
    return tokens


def classify_tokens(tokens: list[str], token_layers: dict[str, str]) -> dict:
    layer_counts = Counter()
    unknown = Counter()
    for token in tokens:
        layer = token_layers.get(token)
        if layer:
            layer_counts[layer] += 1
        else:
            unknown[token] += 1
    total = len(tokens)
    known_total = total - sum(unknown.values())
    result = {field: layer_counts[layer] for layer, field in LAYER_TOKEN_FIELDS.items()}
    result.update(
        {
            "total_tokens": total,
            "readable_coverage_percent": round((known_total / total * 100) if total else 0, 2),
            "forbidden_unknown_tokens": sum(unknown.values()),
            "unknown_token_frequency": dict(sorted(unknown.items())),
        }
    )
    return result


def unknown_clusters(tokens: list[str], token_layers: dict[str, str], *, min_cluster_size: int = 2) -> list[dict]:
    clusters = []
    current: list[str] = []
    start = 0
    for index, token in enumerate(tokens):
        if token not in token_layers:
            if not current:
                start = index
            current.append(token)
            continue
        if len(current) >= min_cluster_size:
            clusters.append({"start_token_index": start, "length": len(current), "tokens": current[:]})
        current = []
    if len(current) >= min_cluster_size:
        clusters.append({"start_token_index": start, "length": len(current), "tokens": current[:]})
    return clusters


def sentence_length_risks(text: str, vocabulary_tokens: set[str], punctuation: set[str], *, warning_tokens: int = 45) -> list[dict]:
    risks = []
    for index, sentence in enumerate(SENTENCE_SPLIT_RE.split(text), start=1):
        sentence = sentence.strip()
        if not sentence:
            continue
        tokens = tokenize_source_text(sentence, vocabulary_tokens, punctuation)
        if len(tokens) > warning_tokens:
            risks.append({"sentence_index": index, "token_count": len(tokens), "text_preview": sentence[:80]})
    return risks


def adaptation_level_for(coverage: float, max_cluster_length: int) -> str:
    if coverage >= 98 and max_cluster_length <= 2:
        return "0-1"
    if coverage >= 95 and max_cluster_length <= 4:
        return "2-3"
    if coverage >= 90:
        return "4"
    return "5-6"


def write_candidate_tsvs(root: Path, unknown_frequency: Counter[str], unknown_units: dict[str, set[str]]) -> None:
    proper_path = root / "proper_noun_candidates.tsv"
    with proper_path.open("w", encoding="utf-8", newline="") as fh:
        fields = ["candidate", "candidate_class", "frequency", "source_units", "status", "notes"]
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for token, count in unknown_frequency.most_common(100):
            if len(token) < 2 or not HANZI_RE.search(token):
                continue
            writer.writerow(
                {
                    "candidate": token,
                    "candidate_class": "review",
                    "frequency": count,
                    "source_units": ",".join(sorted(unknown_units[token])),
                    "status": "candidate",
                    "notes": "Review as person, place, organization, invented term, title, or named object.",
                }
            )

    stretch_path = root / "stretch_candidates.tsv"
    with stretch_path.open("w", encoding="utf-8", newline="") as fh:
        fields = [
            "word",
            "pinyin",
            "rough_meaning",
            "frequency",
            "dispersion",
            "source_units",
            "proposed_layer",
            "reason",
            "replacement_feasibility",
            "status",
        ]
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for token, count in unknown_frequency.most_common(100):
            if not HANZI_RE.search(token):
                continue
            dispersion = len(unknown_units[token])
            writer.writerow(
                {
                    "word": token,
                    "pinyin": "",
                    "rough_meaning": "",
                    "frequency": count,
                    "dispersion": dispersion,
                    "source_units": ",".join(sorted(unknown_units[token])),
                    "proposed_layer": "review",
                    "reason": "Frequent or visible unknown in source profile.",
                    "replacement_feasibility": "unknown",
                    "status": "candidate",
                }
            )


def profile_adaptation_vocabulary(
    adaptation_dir: str | Path,
    *,
    known_path: str | Path = DEFAULT_KNOWN_WORDS,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    personal_known_words_path: str | Path | None = None,
    general_fiction_pack: str | Path | None = None,
    genre_pack: str | Path | None = None,
    setting_pack: str | Path | None = None,
    profession_pack: str | Path | None = None,
    journalism_crime_pack: str | Path | None = None,
    urban_objects_pack: str | Path | None = None,
    book_specific_words_path: str | Path | None = None,
    proper_nouns_path: str | Path | None = None,
    extra_packs: list[str | Path] | None = None,
    target_readable_coverage_percent: float = 98.0,
) -> dict:
    root = Path(adaptation_dir)
    units_dir = root / "source_units"
    vocabulary = load_layered_vocabulary(
        known_path,
        personal_known_words_path=personal_known_words_path,
        general_fiction_pack=general_fiction_pack,
        genre_pack=genre_pack,
        setting_pack=setting_pack,
        profession_pack=profession_pack,
        journalism_crime_pack=journalism_crime_pack,
        urban_objects_pack=urban_objects_pack,
        book_specific_words_path=book_specific_words_path,
        proper_nouns_path=proper_nouns_path,
        extra_packs=extra_packs or [],
    )
    punctuation = load_punctuation(punctuation_path)
    token_layers = vocabulary["token_layers"]
    vocabulary_tokens = set(token_layers)
    unit_reports = []
    all_tokens: list[str] = []
    unknown_frequency: Counter[str] = Counter()
    unknown_units: dict[str, set[str]] = defaultdict(set)
    all_clusters = []
    all_sentence_risks = []

    for path in source_unit_files(units_dir):
        unit_id = path.stem.replace("_source", "")
        text = path.read_text(encoding="utf-8")
        tokens = tokenize_source_text(text, vocabulary_tokens, punctuation)
        classified = classify_tokens(tokens, token_layers)
        clusters = unknown_clusters(tokens, token_layers)
        risks = sentence_length_risks(text, vocabulary_tokens, punctuation)
        max_cluster = max((cluster["length"] for cluster in clusters), default=0)
        classified.update(
            {
                "unit_id": unit_id,
                "unit_path": str(path),
                "source_token_count": classified["total_tokens"],
                "unknown_clusters": clusters,
                "sentence_length_risk": risks,
                "recommended_adaptation_level": adaptation_level_for(
                    classified["readable_coverage_percent"],
                    max_cluster,
                ),
            }
        )
        unit_reports.append(classified)
        all_tokens.extend(tokens)
        for token, count in Counter(token for token in tokens if token not in token_layers).items():
            unknown_frequency[token] += count
            unknown_units[token].add(unit_id)
        for cluster in clusters:
            all_clusters.append({"unit_id": unit_id, **cluster})
        for risk in risks:
            all_sentence_risks.append({"unit_id": unit_id, **risk})

    total_report = classify_tokens(all_tokens, token_layers)
    total_report.update(
        {
            "schema_version": 1,
            "generated_at": utc_now(),
            "adaptation_dir": str(root),
            "known_words_path": str(Path(known_path)),
            "personal_known_words_path": str(Path(personal_known_words_path)) if personal_known_words_path else None,
            "vocabulary_profile": vocabulary.get("vocabulary_profile", "public"),
            "learner_profile_name": vocabulary.get("learner_profile_name"),
            "target_readable_coverage_percent": target_readable_coverage_percent,
            "unit_count": len(unit_reports),
            "units": unit_reports,
            "top_unknown_tokens_by_frequency": [
                {"token": token, "count": count} for token, count in unknown_frequency.most_common(50)
            ],
            "top_unknown_tokens_by_dispersion": [
                {"token": token, "unit_count": len(units), "units": sorted(units), "count": unknown_frequency[token]}
                for token, units in sorted(unknown_units.items(), key=lambda item: (-len(item[1]), item[0]))[:50]
            ],
            "unknown_clusters": all_clusters[:100],
            "unknown_cluster_count": len(all_clusters),
            "sentence_length_risks": all_sentence_risks[:100],
            "sentence_length_risk_count": len(all_sentence_risks),
            "recommended_next_step": "review_candidates" if total_report["readable_coverage_percent"] < target_readable_coverage_percent else "minimal_adaptation",
        }
    )
    write_json(root / "vocabulary_profile_baseline.json", total_report)
    summary = [
        f"# Vocabulary Profile Baseline: {root.name}",
        "",
        f"- Vocabulary profile: `{total_report['vocabulary_profile']}`",
        f"- Total source tokens: {total_report['total_tokens']}",
        f"- Readable coverage: {total_report['readable_coverage_percent']}%",
        f"- Forbidden unknown tokens: {total_report['forbidden_unknown_tokens']}",
        f"- Unknown clusters: {total_report['unknown_cluster_count']}",
        f"- Sentence-length risks: {total_report['sentence_length_risk_count']}",
        "",
        "## Top Unknown Tokens",
        "",
    ]
    for item in total_report["top_unknown_tokens_by_frequency"][:25]:
        summary.append(f"- `{item['token']}`: {item['count']}")
    (root / "vocabulary_profile_baseline.md").write_text("\n".join(summary).rstrip() + "\n", encoding="utf-8")
    write_candidate_tsvs(root, unknown_frequency, unknown_units)
    return total_report
