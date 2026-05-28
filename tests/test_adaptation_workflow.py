from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.adaptation_tools import import_epub_for_adaptation, profile_adaptation_vocabulary
from scripts.novel_tools import ROOT


def write_minimal_epub(path: Path) -> None:
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="nav"/>
    <itemref idref="chapter1"/>
  </spine>
</package>
"""
    nav = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><nav>目录</nav></body></html>
"""
    chapter = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h1>第一章</h1>
    <p>林安 看 失物柜 。</p>
    <p>她 在 上海 问 一个 问题 。</p>
  </body>
</html>
"""
    with zipfile.ZipFile(path, "w") as zf:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, "application/epub+zip")
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.opf", opf)
        zf.writestr("OEBPS/nav.xhtml", nav)
        zf.writestr("OEBPS/chapter1.xhtml", chapter)


class AdaptationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_epub_import_creates_source_map_and_units(self) -> None:
        epub = self.root / "source.epub"
        write_minimal_epub(epub)
        report = import_epub_for_adaptation(
            epub,
            "test-adaptation",
            adaptations_dir=self.root / "adaptations",
            rights_status="private_study",
            min_unit_tokens=1,
            max_unit_tokens=50,
            copy_source_private=True,
        )
        adaptation = self.root / "adaptations" / "test-adaptation"
        self.assertEqual(report["source_unit_count"], 1)
        self.assertTrue((adaptation / "source_map.json").exists())
        self.assertTrue((adaptation / "adaptation_config.json").exists())
        self.assertTrue((adaptation / "source_private" / "source.epub").exists())
        unit_text = (adaptation / "source_units" / "unit_001_source.md").read_text(encoding="utf-8")
        self.assertIn("林安 看 失物柜", unit_text)

    def test_adaptation_profile_counts_layers_and_candidates(self) -> None:
        known = self.root / "known_words.txt"
        known.write_text("我\n你\n在\n看\n了\n这里\n", encoding="utf-8")
        personal = self.root / "personal.txt"
        personal.write_text("犹豫\n", encoding="utf-8")
        general = self.root / "general.txt"
        general.write_text("沉默\n", encoding="utf-8")
        proper = self.root / "proper.txt"
        proper.write_text("林安\n", encoding="utf-8")
        adaptation = self.root / "adaptations" / "profile"
        units = adaptation / "source_units"
        units.mkdir(parents=True)
        (units / "unit_001_source.md").write_text("林安 看 犹豫 沉默 黑门 黑门 。\n我 在 这里 。\n", encoding="utf-8")

        report = profile_adaptation_vocabulary(
            adaptation,
            known_path=known,
            personal_known_words_path=personal,
            general_fiction_pack=general,
            proper_nouns_path=proper,
        )
        self.assertEqual(report["proper_noun_tokens"], 1)
        self.assertEqual(report["personal_known_tokens"], 1)
        self.assertEqual(report["general_fiction_stretch_tokens"], 1)
        self.assertEqual(report["forbidden_unknown_tokens"], 2)
        self.assertEqual(report["top_unknown_tokens_by_frequency"][0]["token"], "黑门")
        self.assertTrue((adaptation / "vocabulary_profile_baseline.json").exists())
        proper_candidates = (adaptation / "proper_noun_candidates.tsv").read_text(encoding="utf-8")
        self.assertIn("黑门", proper_candidates)

    def test_adaptation_profile_segments_natural_chinese_source(self) -> None:
        known = self.root / "known_words.txt"
        known.write_text("我\n看\n市场\n价格\n上升\n", encoding="utf-8")
        adaptation = self.root / "adaptations" / "natural"
        units = adaptation / "source_units"
        units.mkdir(parents=True)
        (units / "unit_001_source.md").write_text("我看市场价格上升。陌生词出现。\n", encoding="utf-8")

        report = profile_adaptation_vocabulary(adaptation, known_path=known)
        self.assertGreater(report["readable_coverage_percent"], 40)
        unknowns = report["unknown_token_frequency"]
        self.assertNotIn("我看市场价格上升陌生词出现", unknowns)
        self.assertTrue({"陌生词", "陌生"} & set(unknowns))

    def test_adaptation_profile_separates_non_hanzi_support_tokens(self) -> None:
        known = self.root / "known_words.txt"
        known.write_text("我\n看\n市场\n", encoding="utf-8")
        adaptation = self.root / "adaptations" / "latin"
        units = adaptation / "source_units"
        units.mkdir(parents=True)
        (units / "unit_001_source.md").write_text("我看市场。market growth 2026。\n", encoding="utf-8")

        report = profile_adaptation_vocabulary(adaptation, known_path=known)
        self.assertEqual(report["forbidden_unknown_tokens"], 0)
        self.assertGreaterEqual(report["ignored_non_hanzi_token_count"], 3)
        self.assertIn("market", report["ignored_non_hanzi_token_frequency"])

    def test_quality_gate_requires_source_fidelity_when_requested(self) -> None:
        known = self.root / "known_words.txt"
        known.write_text("我\n你\n看\n", encoding="utf-8")
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 你 。\n", encoding="utf-8")
        planning = manuscript / "planning"
        planning.mkdir()
        (planning / "chapter_01_vocab_plan.md").write_text("# Plan\n", encoding="utf-8")
        quality = manuscript / "quality"
        quality.mkdir()
        (quality / "lead_quality_decision.md").write_text("Final decision: PASS\n", encoding="utf-8")

        summary_path = quality / "quality_gate_summary.json"
        subprocess.run(
            [
                sys.executable,
                "scripts/run_quality_gate.py",
                "--manuscript",
                str(manuscript),
                "--known",
                str(known),
                "--require-source-fidelity",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["source_fidelity_required"])
        self.assertFalse(summary["source_fidelity_reviewed"])
        self.assertFalse(summary["ready_for_epub"])

        (quality / "source_fidelity_report.md").write_text("Fidelity decision: PASS\n", encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "scripts/run_quality_gate.py",
                "--manuscript",
                str(manuscript),
                "--known",
                str(known),
                "--require-source-fidelity",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["source_fidelity_reviewed"])
        self.assertTrue(summary["ready_for_epub"])

    def test_private_adaptation_sources_are_gitignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("adaptations/*/source_private/", ignore)
        self.assertIn("adaptations/*/source_units/*_source.md", ignore)


if __name__ == "__main__":
    unittest.main()
