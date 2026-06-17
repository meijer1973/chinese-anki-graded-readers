from __future__ import annotations

import argparse
from pathlib import Path

try:
    from novel_tools import DEFAULT_KNOWN_WORDS, load_known_words, load_optional_words, write_json
except ModuleNotFoundError:
    from scripts.novel_tools import DEFAULT_KNOWN_WORDS, load_known_words, load_optional_words, write_json


CATEGORIES: dict[str, set[str]] = {
    "action_verbs": {
        "找",
        "看",
        "走",
        "跑",
        "拿",
        "打开",
        "抓",
        "带",
        "跟踪",
        "追踪",
        "搜查",
        "搜索",
        "拍照",
        "观察",
        "发布",
        "发表",
        "报警",
        "作证",
    },
    "emotion_words": {
        "爱",
        "怕",
        "害怕",
        "担心",
        "开心",
        "高兴",
        "生气",
        "痛苦",
        "快乐",
        "讨厌",
        "相信",
        "信任",
    },
    "crime_nouns": {
        "案",
        "案子",
        "案件",
        "犯罪",
        "谋杀",
        "凶手",
        "嫌犯",
        "受害人",
        "凶器",
        "警方",
        "警察局",
        "谋杀案",
        "被告",
        "人质",
        "车祸",
        "警报",
    },
    "evidence_nouns": {
        "证据",
        "线索",
        "文件",
        "资料",
        "档案",
        "录音",
        "录像",
        "镜头",
        "摄像机",
        "密码",
        "指纹",
        "血迹",
        "痕迹",
        "证词",
        "签名",
    },
    "journalism_nouns": {
        "采访",
        "报道",
        "报纸",
        "文章",
        "编辑",
        "标题",
        "来源",
        "读者",
        "媒体",
        "网站",
        "记者",
        "线人",
        "在场",
        "审判",
        "联络",
        "网络",
        "观点",
        "通话",
    },
    "movement_location_words": {
        "上海",
        "外滩",
        "黄浦江",
        "南京路",
        "人民广场",
        "地铁",
        "地铁站",
        "街道",
        "小巷",
        "河边",
        "桥",
        "公园",
        "店",
        "门口",
        "屋顶",
        "办公室",
        "警察局",
    },
    "relationship_words": {
        "朋友",
        "妈妈",
        "爸爸",
        "父母",
        "哥哥",
        "妹妹",
        "兄弟",
        "同事",
        "邻居",
        "房东",
        "老板",
        "读者",
        "证人",
    },
    "conflict_verbs": {
        "威胁",
        "伤害",
        "保护",
        "阻止",
        "骗",
        "否认",
        "确认",
        "判断",
        "公开",
        "保密",
        "举报",
        "透露",
        "合法",
        "辩护",
        "证实",
        "表明",
    },
    "fantasy_mechanism_words": {
        "雨票",
        "黑票",
        "灵灯",
        "影门",
        "黑雾",
        "白光",
        "魔法",
        "灵魂",
        "鬼魂",
        "幻影",
        "结界",
        "护符",
        "咒语",
    },
    "dialogue_alternatives": {
        "问",
        "回答",
        "告诉",
        "解释",
        "承认",
        "否认",
        "透露",
        "发誓",
        "道歉",
        "谈",
        "谈谈",
    },
}


def collect_words(known: str | Path, packs: list[str | Path]) -> set[str]:
    words = set(load_known_words(known))
    for pack in packs:
        words.update(load_optional_words(pack))
    return words


def build_report(known: str | Path, packs: list[str | Path], required: list[str]) -> dict:
    available = collect_words(known, packs)
    categories = {
        name: sorted(words & available)
        for name, words in CATEGORIES.items()
    }
    missing_required = sorted(word for word in required if word not in available)
    warnings = []
    if missing_required:
        warnings.append(
            {
                "type": "missing_required_plot_words",
                "message": "The premise asks for words that are not in the active known or approved stretch vocabulary.",
                "tokens": missing_required,
            }
        )
    for name in ("crime_nouns", "evidence_nouns", "journalism_nouns"):
        if len(categories[name]) < 5:
            warnings.append(
                {
                    "type": "thin_affordance_category",
                    "category": name,
                    "available_count": len(categories[name]),
                }
            )

    return {
        "schema_version": 1,
        "known_words_path": str(Path(known)),
        "packs": [str(Path(pack)) for pack in packs],
        "required_words": required,
        "available_required_words": sorted(word for word in required if word in available),
        "missing_required_words": missing_required,
        "categories": categories,
        "category_counts": {name: len(words) for name, words in categories.items()},
        "warnings": warnings,
        "note": "This report is planning evidence, not a literary decision.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report which plot functions the active vocabulary can support.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--packs", nargs="*", default=[])
    parser.add_argument("--required", nargs="*", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = build_report(args.known, args.packs, args.required)
    write_json(args.out, report)
    print(
        "categories={categories} missing_required={missing}".format(
            categories=len(report["categories"]),
            missing=len(report["missing_required_words"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
