from __future__ import annotations

import bz2
import csv
import gzip
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import jieba
from opencc import OpenCC
from pypinyin import Style, lazy_pinyin

from apply_meaning_cleanup_updates import cleaned_meaning
from sentence_example_overrides import (
    SENTENCE_EXAMPLE_OVERRIDES,
    SENTENCE_PINYIN_OVERRIDES,
)


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WORD_LIST = ROOT / "word list chinese.txt"

CEDICT_GZ = DATA / "cedict_ts.u8.gz"
CMN_SENTENCES = DATA / "cmn_sentences.tsv.bz2"
ENG_SENTENCES = DATA / "eng_sentences.tsv.bz2"
CMN_ENG_LINKS = DATA / "cmn-eng_links.tsv.bz2"

REVIEW_OUTPUT = ROOT / "anki_chinese_review.tsv"
IMPORT_OUTPUT = ROOT / "anki_chinese_import.tsv"
REPORT_OUTPUT = ROOT / "enrichment_report.txt"

TO_SIMPLIFIED = OpenCC("t2s")
jieba.setLogLevel(logging.WARNING)

FIELDS = [
    "Word",
    "Pinyin",
    "Meaning",
    "Example",
    "Example Pinyin",
    "Example Meaning",
    "Tags",
]

MANUAL_ENTRIES: dict[str, tuple[str, str]] = {
    "很多": ("hen3 duo1", "many; a lot of"),
    "来说": ("lai2 shuo1", "as far as ... is concerned; speaking in terms of"),
    "还要": ("hai2 yao4", "still need or want; also have to; in addition"),
    "试试": ("shi4 shi4", "to try; to give it a try"),
    "很快": ("hen3 kuai4", "very fast; very soon"),
    "任何人": ("ren4 he2 ren2", "anyone; anybody"),
    "这次": ("zhe4 ci4", "this time"),
    "想想": ("xiang3 xiang3", "to think about; to give something some thought"),
    "第三": ("di4 san1", "third"),
    "某个": ("mou3 ge4", "a certain; some particular"),
    "听听": ("ting1 ting1", "to listen; to hear"),
    "手上": ("shou3 shang4", "in hand; on one's hand; currently held"),
    "一刻": ("yi1 ke4", "a moment; a quarter hour"),
    "脸上": ("lian3 shang4", "on one's face"),
    "问问": ("wen4 wen4", "to ask; to ask around"),
    "瞧瞧": ("qiao2 qiao2", "to take a look; to have a look"),
    "第四": ("di4 si4", "fourth"),
    "查理": ("cha2 li3", "Charlie"),
    "我会": ("wo3 hui4", "I can; I will"),
    "警长": ("jing3 zhang3", "sheriff; police chief; police sergeant"),
    "车上": ("che1 shang4", "in or on a car; aboard a vehicle"),
    "留下来": ("liu2 xia4 lai2", "to stay behind; to remain; to stay"),
    "放在": ("fang4 zai4", "to put or place in, on, or at"),
    "猜猜": ("cai1 cai1", "to guess; to take a guess"),
    "趴下": ("pa1 xia4", "to lie face down; to get down"),
    "城里": ("cheng2 li3", "in the city; inside town"),
    "聊聊": ("liao2 liao2", "to chat; to have a chat"),
    "见见": ("jian4 jian4", "to meet; to see briefly"),
    "小家伙": ("xiao3 jia1 huo5", "little guy; little fellow"),
    "乔伊": ("qiao2 yi1", "Joey"),
    "船上": ("chuan2 shang4", "on a boat or ship"),
    "救救": ("jiu4 jiu4", "to save; to help"),
    "查查": ("cha2 cha2", "to check; to look into"),
    "一分": ("yi1 fen1", "one point; one minute; one cent; one part"),
    "一整天": ("yi1 zheng3 tian1", "all day; the whole day"),
    "威尔": ("wei1 er3", "Will"),
    "调查局": ("diao4 cha2 ju2", "bureau of investigation"),
    "你家": ("ni3 jia1", "your home; your family"),
    "尝尝": ("chang2 chang2", "to taste; to try a taste"),
    "偷走": ("tou1 zou3", "to steal; to steal away"),
    "屋里": ("wu1 li3", "inside the room or house"),
    "皮特": ("pi2 te4", "Pete"),
    "鲍勃": ("bao4 bo2", "Bob"),
    "小妞": ("xiao3 niu1", "girl; chick (colloquial, sometimes impolite)"),
    "墙上": ("qiang2 shang4", "on the wall"),
    "手中": ("shou3 zhong1", "in one's hand; in hand"),
}

MANUAL_EXAMPLES: dict[str, tuple[str, str]] = {
    "是的": ("是的，我同意你的看法。", "Yes, I agree with your view."),
    "哥们": ("哥们，你今天有空吗？", "Buddy, are you free today?"),
    "某种": ("他有某种特别的能力。", "He has a certain special ability."),
    "不对": ("这个答案不对。", "This answer is not correct."),
    "神经": ("长期压力会影响神经。", "Long-term stress can affect the nerves."),
    "有的": ("有的人喜欢茶，有的人喜欢咖啡。", "Some people like tea, and some like coffee."),
    "一一": ("他把问题一一回答了。", "He answered the questions one by one."),
    "基地": ("他们在山里建立了一个基地。", "They built a base in the mountains."),
    "辈子": ("我这辈子不会忘记你。", "I will not forget you in this lifetime."),
    "辩护": ("律师为他辩护。", "The lawyer defended him."),
    "对劲": ("这件事有点不对劲。", "Something about this is a bit off."),
    "威尔": ("威尔明天会来。", "Will will come tomorrow."),
    "丹尼": ("丹尼喜欢打篮球。", "Danny likes playing basketball."),
    "百万": ("这座城市有一百万人口。", "This city has a population of one million."),
    "西德": ("西德曾经是一个国家。", "West Germany was once a country."),
    "说说": ("你能说说你的计划吗？", "Can you talk about your plan?"),
    "什么的": ("我喜欢音乐、电影什么的。", "I like music, movies, and things like that."),
    "牛仔": ("牛仔骑着马穿过草原。", "The cowboy rode a horse across the prairie."),
    "罪名": ("他否认了所有罪名。", "He denied all the charges."),
    "皮特": ("皮特正在准备晚饭。", "Pete is preparing dinner."),
    "大哥": ("大哥，请帮我一下。", "Big brother, please help me."),
    "评委": ("评委给了她很高的分数。", "The judges gave her a high score."),
    "偶像": ("他是很多年轻人的偶像。", "He is an idol for many young people."),
    "上校": ("上校命令士兵集合。", "The colonel ordered the soldiers to assemble."),
    "警长": ("警长正在调查这个案子。", "The sheriff is investigating this case."),
    "受害人": ("受害人需要我们的帮助。", "The victim needs our help."),
    "陛下": ("陛下，请您听我解释。", "Your Majesty, please listen to my explanation."),
    "上尉": ("上尉带队前进。", "The captain led the team forward."),
    "保姆": ("保姆正在照顾孩子。", "The nanny is taking care of the child."),
    "神像": ("庙里有一尊古老的神像。", "There is an ancient statue of a deity in the temple."),
    "阁下": ("阁下有什么建议？", "Do you have any suggestions, Your Excellency?"),
    "乔伊": ("乔伊今天没有来上课。", "Joey did not come to class today."),
    "贱人": ("他不该用“贱人”这种话骂人。", 'He should not insult people with words like "bitch."'),
    "嫌犯": ("嫌犯被警察带走了。", "The suspect was taken away by the police."),
    "福尔摩斯": ("福尔摩斯是著名的侦探。", "Sherlock Holmes is a famous detective."),
    "强奸": ("她勇敢地报告了强奸案。", "She bravely reported the rape case."),
    "中尉": ("中尉向上校报告情况。", "The lieutenant reported the situation to the colonel."),
    "直播": ("这场比赛正在直播。", "This match is being broadcast live."),
    "坐牢": ("他因为诈骗坐牢三年。", "He spent three years in prison for fraud."),
    "展现": ("这张照片展现了城市的变化。", "This photo shows the city's changes."),
    "证词": ("她的证词非常重要。", "Her testimony is very important."),
    "调查局": ("调查局公布了新的报告。", "The bureau of investigation released a new report."),
    "事务所": ("他在一家律师事务所工作。", "He works at a law firm."),
    "殿下": ("殿下已经到达大厅。", "Your Highness has arrived at the hall."),
    "克莱尔": ("克莱尔正在学中文。", "Claire is studying Chinese."),
    "大赛": ("她参加了歌唱大赛。", "She entered a singing competition."),
    "胸部": ("运动时要保护胸部。", "Protect your chest when exercising."),
    "小妞": ("在一些语境里，“小妞”听起来不礼貌。", 'In some contexts, "chick" sounds impolite.'),
    "指挥官": ("指挥官下达了撤退命令。", "The commander gave the order to retreat."),
    "豁免权": ("外交官享有一定的豁免权。", "Diplomats have certain immunity."),
    "郡": ("这个郡有很多古老的建筑。", "This county has many old buildings."),
}


@dataclass(frozen=True)
class CedictEntry:
    pinyin: str
    definitions: tuple[str, ...]


@dataclass(frozen=True)
class Example:
    chinese: str
    pinyin: str
    english: str
    source: str


def clean_field(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\t", " ")).strip()


def is_hanzi(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff"


def normalize_pinyin_numbers(value: str) -> str:
    value = clean_field(value)
    return value.replace("u:", "ü").replace("U:", "Ü")


CHINESE_SENTENCE_ENDING = "。！？…」』”）】》"


def normalize_chinese_sentence(value: str) -> str:
    value = clean_field(value)
    value = value.replace("?", "？").replace("!", "！")
    if value.endswith("."):
        value = value[:-1].rstrip() + "。"
    if value and value[-1] not in CHINESE_SENTENCE_ENDING and is_hanzi(value[-1]):
        value += "。"
    return value


def generated_pinyin(text: str) -> str:
    if text in SENTENCE_PINYIN_OVERRIDES:
        return SENTENCE_PINYIN_OVERRIDES[text]

    pinyin = lazy_pinyin(
        text,
        style=Style.TONE3,
        neutral_tone_with_five=True,
        errors="default",
    )
    joined = " ".join(pinyin)
    return re.sub(r"\s+([。！？!?，,；;：:）】》”])", r"\1", joined)


def read_words() -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for line in WORD_LIST.read_text(encoding="utf-8-sig").splitlines():
        word = line.strip()
        if word and word not in seen:
            words.append(word)
            seen.add(word)
    return words


def parse_cedict() -> dict[str, list[CedictEntry]]:
    entries: dict[str, list[CedictEntry]] = defaultdict(list)
    pattern = re.compile(r"^(\S+)\s+(\S+)\s+\[(.+?)\]\s+/(.*)/$")

    with gzip.open(CEDICT_GZ, "rt", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if not match:
                continue
            simplified = match.group(2)
            pinyin = normalize_pinyin_numbers(match.group(3))
            definitions = tuple(
                clean_field(definition)
                for definition in match.group(4).split("/")
                if clean_field(definition)
            )
            if definitions:
                entries[simplified].append(CedictEntry(pinyin, definitions))

    return entries


def concise_definitions(entries: list[CedictEntry]) -> str:
    definitions: list[str] = []
    fallback_definitions: list[str] = []

    low_value_prefixes = (
        "cl:",
        "classifier",
        "surname ",
        "variant of ",
        "old variant of ",
        "abbr. for ",
        "see also ",
    )

    for entry in entries:
        for raw_definition in entry.definitions:
            definition = re.sub(r"\(Note: [^)]*\)", "", raw_definition)
            definition = re.sub(r"\(Taiwan pr\. \[[^\]]+\]\)", "", definition)
            definition = re.sub(r"\bTaiwan pr\. \[[^\]]+\]", "", definition)
            definition = clean_field(definition).strip(" ;")
            if not definition:
                continue
            lowered = definition.lower()
            if definition not in fallback_definitions:
                fallback_definitions.append(definition)
            if (
                lowered.startswith(low_value_prefixes)
                or re.search(r"\bsurname\b", definition, flags=re.IGNORECASE)
                or lowered.startswith("(tw)")
                or lowered.startswith("tw ")
                or lowered.startswith("taiwanese ")
            ):
                continue
            if definition not in definitions:
                definitions.append(definition)

    chosen = definitions or fallback_definitions
    joined = "; ".join(chosen[:5])
    return joined[:190].rstrip(" ;")


def entry_pinyin(entries: list[CedictEntry]) -> str:
    readings: list[str] = []
    for entry in entries:
        if entry.pinyin not in readings:
            readings.append(entry.pinyin)
    return " / ".join(readings[:6])


def fallback_meaning(word: str, entries_by_word: dict[str, list[CedictEntry]]) -> str:
    pieces: list[str] = []
    for char in word:
        char_entries = entries_by_word.get(char)
        if not char_entries:
            continue
        definition = concise_definitions(char_entries).split(";")[0]
        if definition:
            pieces.append(f"{char}: {definition}")

    if pieces:
        return "Character meanings: " + "; ".join(pieces[:6])
    return "Needs review"


def load_links() -> tuple[dict[int, list[int]], set[int], set[int]]:
    links_by_cmn: dict[int, list[int]] = defaultdict(list)
    cmn_ids: set[int] = set()
    eng_ids: set[int] = set()

    with bz2.open(CMN_ENG_LINKS, "rt", encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            cmn_id = int(parts[0])
            eng_id = int(parts[1])
            links_by_cmn[cmn_id].append(eng_id)
            cmn_ids.add(cmn_id)
            eng_ids.add(eng_id)

    return links_by_cmn, cmn_ids, eng_ids


def load_sentences(path: Path, wanted_ids: set[int]) -> dict[int, str]:
    sentences: dict[int, str] = {}
    with bz2.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) != 3:
                continue
            sentence_id = int(parts[0])
            if sentence_id in wanted_ids:
                sentences[sentence_id] = clean_field(parts[2])
    return sentences


def build_examples() -> tuple[list[tuple[int, str, str, str]], dict[str, list[int]]]:
    links_by_cmn, cmn_ids, eng_ids = load_links()
    english = load_sentences(ENG_SENTENCES, eng_ids)
    mandarin = load_sentences(CMN_SENTENCES, cmn_ids)

    records: list[tuple[int, str, str, str]] = []
    for cmn_id, cmn_text in mandarin.items():
        translations = [
            english[eng_id]
            for eng_id in links_by_cmn.get(cmn_id, [])
            if eng_id in english
        ]
        if not translations:
            continue
        eng_text = min(translations, key=len)
        cmn_text = normalize_chinese_sentence(TO_SIMPLIFIED.convert(cmn_text))
        pinyin = generated_pinyin(cmn_text)
        records.append((cmn_id, cmn_text, pinyin, eng_text))

    records.sort(key=lambda row: (len(row[1]), len(row[3]), row[0]))

    char_index: dict[str, list[int]] = defaultdict(list)
    for index, (_, cmn_text, _, _) in enumerate(records):
        for char in set(cmn_text):
            if is_hanzi(char):
                char_index[char].append(index)

    return records, char_index


TINY_TRANSLATIONS = {
    "ah!",
    "ah.",
    "hello!",
    "hello.",
    "hi!",
    "hi.",
    "huh?",
    "no!",
    "no.",
    "oh!",
    "oh.",
    "ok?",
    "okay?",
    "ta!",
    "thanks!",
    "yes!",
    "yes.",
}

EDGE_FILLER_HANZI = set("啊哦噢喔呀唉哎嗨嘿喂嗯呃欸诶吧嘛呢啦了的")


def trim_edge_fillers(hanzi_text: str) -> str:
    while hanzi_text and hanzi_text[0] in EDGE_FILLER_HANZI:
        hanzi_text = hanzi_text[1:]
    while hanzi_text and hanzi_text[-1] in EDGE_FILLER_HANZI:
        hanzi_text = hanzi_text[:-1]
    return hanzi_text


def is_good_example_candidate(word: str, chinese: str, english: str) -> bool:
    hanzi_text = "".join(char for char in chinese if is_hanzi(char))
    if hanzi_text == word:
        return False
    if trim_edge_fillers(hanzi_text) == word:
        return False
    if len(hanzi_text) < max(4, len(word) + 2):
        return False
    if english.strip().lower() in TINY_TRANSLATIONS:
        return False
    return True


def contains_word(word: str, chinese: str) -> bool:
    if word not in chinese:
        return False
    if len(word) == 1:
        return True
    return word in jieba.lcut(chinese)


def find_example(
    word: str,
    records: list[tuple[int, str, str, str]],
    char_index: dict[str, list[int]],
) -> Example:
    if word in SENTENCE_EXAMPLE_OVERRIDES:
        chinese, english = SENTENCE_EXAMPLE_OVERRIDES[word]
        return Example(chinese, generated_pinyin(chinese), english, "manual")

    if word in MANUAL_EXAMPLES:
        chinese, english = MANUAL_EXAMPLES[word]
        return Example(chinese, generated_pinyin(chinese), english, "manual")

    chars = [char for char in dict.fromkeys(word) if is_hanzi(char)]
    candidates: list[int] = []
    if chars:
        rarest_char = min(chars, key=lambda char: len(char_index.get(char, [])))
        candidates = char_index.get(rarest_char, [])

    for index in candidates:
        _, chinese, pinyin, english = records[index]
        if contains_word(word, chinese) and is_good_example_candidate(word, chinese, english):
            return Example(chinese, pinyin, english, "tatoeba")

    chinese = f"我想学习“{word}”这个词。"
    return Example(
        chinese=chinese,
        pinyin=generated_pinyin(chinese),
        english=f'I want to learn the word "{word}."',
        source="generated",
    )


def write_tsv(path: Path, rows: list[list[str]], include_header: bool) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        if include_header:
            writer.writerow(FIELDS)
        writer.writerows(rows)


def main() -> None:
    words = read_words()
    entries_by_word = parse_cedict()
    example_records, char_index = build_examples()

    rows: list[list[str]] = []
    missing_exact_meaning = 0
    manual_meanings = 0
    generated_examples = 0
    manual_examples = 0

    for word in words:
        entries = entries_by_word.get(word)
        if entries:
            pinyin = entry_pinyin(entries)
            meaning = concise_definitions(entries)
            meaning_tag = "cedict"
        elif word in MANUAL_ENTRIES:
            pinyin, meaning = MANUAL_ENTRIES[word]
            meaning_tag = "manual_meaning"
            manual_meanings += 1
        else:
            pinyin = generated_pinyin(word)
            meaning = fallback_meaning(word, entries_by_word)
            meaning_tag = "needs_meaning_review"
            missing_exact_meaning += 1

        meaning = cleaned_meaning(word, meaning)

        example = find_example(word, example_records, char_index)
        if example.source == "generated":
            generated_examples += 1
        elif example.source == "manual":
            manual_examples += 1

        tags = f"chinese {meaning_tag} {example.source}"
        rows.append(
            [
                word,
                pinyin,
                meaning,
                example.chinese,
                example.pinyin,
                example.english,
                tags,
            ]
        )

    write_tsv(REVIEW_OUTPUT, rows, include_header=True)
    write_tsv(IMPORT_OUTPUT, rows, include_header=False)

    report = [
        f"Input rows after dedupe: {len(words)}",
        f"Output rows: {len(rows)}",
        f"Rows using manual meaning: {manual_meanings}",
        f"Rows still needing meaning review: {missing_exact_meaning}",
        f"Rows using manual example sentence: {manual_examples}",
        f"Rows using generated example sentence: {generated_examples}",
        "",
        "Files:",
        f"- {REVIEW_OUTPUT.name}: TSV with header for review",
        f"- {IMPORT_OUTPUT.name}: TSV without header for Anki import",
        "",
        "Columns:",
        "\t".join(FIELDS),
        "",
        "Sources:",
        "- CC-CEDICT: https://cc-cedict.org/editor/editor.php?handler=Download",
        "- Tatoeba Mandarin-English exports: https://downloads.tatoeba.org/exports/per_language/cmn/",
    ]
    REPORT_OUTPUT.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
