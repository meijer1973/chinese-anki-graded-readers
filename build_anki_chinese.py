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

# Prioritize common readings when dictionary ordering favors rare senses.
WORD_PINYIN_OVERRIDES: dict[str, str] = {
    # User-selected novel characters, 2026-10-20.
    "灿": "can4",
    "眶": "kuang4",
    "荧": "ying2",
    "蹬": "deng1",
    "凝": "ning2",
    "咫": "zhi3",
    "哧": "chi1",
    "拱": "gong3",
    "梳": "shu1",
    "沸": "fei4",
    "渔": "yu2",
    "烬": "jin4",
    "皙": "xi1",
    "卿": "qing1",
    "嘤": "ying1",
    "拇": "mu3",
    "肆": "si4",
    "锡": "xi1",
    "丘": "qiu1",
    "惚": "hu1",
    "戛": "jia2",
    "撅": "jue1",
    "撸": "lu1",
    # Second user-selected vocabulary batch, 2026-10-19.
    "笼子": "long2 zi5",
    "咽": "yan4 / yan1 / ye4",
    "玫瑰": "mei2 gui5",
    "刘": "liu2",
    "梁": "liang2",
    "出息": "chu1 xi5",
    "吾": "wu2",
    "奥运": "ao4 yun4",
    "奥运会": "ao4 yun4 hui4",
    "下载": "xia4 zai4",
    "戚": "qi1",
    "屏住": "bing3 zhu4",
    "本次": "ben3 ci4",
    "曝光": "bao4 guang1",
    "曝": "bao4 / pu4",
    # User-selected vocabulary additions, 2026-10-19.
    "丝毫": "si1 hao2",
    "结实": "jie1 shi5",
    "宠物": "chong3 wu4",
    "鞠躬": "ju1 gong1",
    "游走": "you2 zou3",
    "草丛": "cao3 cong2",
    "边缘": "bian1 yuan2",
    "小心翼翼": "xiao3 xin1 yi4 yi4",
    "嘟囔": "du1 nang5",
    "嫌弃": "xian2 qi4",
    "以上": "yi3 shang4",
    "发育": "fa1 yu4",
    "闪烁": "shan3 shuo4",
    "好歹": "hao3 dai3",
    "退役": "tui4 yi4",
    "联赛": "lian2 sai4",
    "元素": "yuan2 su4",
    "拉扯": "la1 che5",
    "提示": "ti2 shi4",
    "后排": "hou4 pai2",
    "点燃": "dian3 ran2",
    "摄影": "she4 ying3",
    "抽签": "chou1 qian1",
    "胡萝卜": "hu2 luo2 bo5",
    "替补": "ti4 bu3",
    "观众席": "guan1 zhong4 xi2",
    "媳妇": "xi2 fu5 / xi2 fu4",
    "理所当然": "li3 suo3 dang1 ran2",
    "开幕": "kai1 mu4",
    "一幕": "yi2 mu4",
    "节奏": "jie2 zou4",
    "逐渐": "zhu2 jian4",
    "名额": "ming2 e2",
    "过于": "guo4 yu2",
    "灵活": "ling2 huo2",
    "质疑": "zhi4 yi2",
    "版本": "ban3 ben3",
    "总结": "zong3 jie2",
    "如今": "ru2 jin1",
    "落后": "luo4 hou4",
    "复活": "fu4 huo2",
    "握手": "wo4 shou3",
    "爆发": "bao4 fa1",
    "占据": "zhan4 ju4",
    "素质": "su4 zhi4",
    "官方": "guan1 fang1",
    "正面": "zheng4 mian4",
    "当前": "dang1 qian2",
    # User-selected Falling Into Your Smile characters, 2026-10-17.
    "嗖": "sou1",
    "嘶": "si1",
    "扒": "ba1 / pa2",
    "咕": "gu1",
    "僧": "seng1",
    "嗅": "xiu4",
    "烁": "shuo4",
    "躬": "gong1",
    "鞠": "ju1",
    "撩": "liao1 / liao2",
    "芒": "mang2",
    "颊": "jia2",
    "宵": "xiao1",
    "岚": "lan2",
    "峡": "xia2",
    "搓": "cuo1",
    "撇": "pie1 / pie3",
    "歹": "dai3",
    "萌": "meng2",
    "踮": "dian3",
    "凳": "deng4",
    "嗳": "ai3 / ai4",
    "戳": "chuo1",
    "敛": "lian3",
    "耸": "song3",
    "蹿": "cuan1",
    "捶": "chui2",
    "狸": "li2",
    "砰": "peng1",
    "伐": "fa2",
    "喵": "miao1",
    "噜": "lu1",
    "腻": "ni4",
    "译": "yi4",
    "漉": "lu4",
    "绵": "mian2",
    "赅": "gai1",
    "颚": "e4",
    "叼": "diao1",
    "叽": "ji1",
    "咸": "xian2",
    "扛": "kang2 / gang1",
    "揪": "jiu1",
    "涨": "zhang3 / zhang4",
    "猝": "cu4",
    "膛": "tang2",
    "晰": "xi1",
    "曜": "yao4",
    "衩": "cha3 / cha4",
    "巅": "dian1",
    "揣": "chuai1 / chuai3",
    "吁": "xu1 / yu4",
    "葱": "cong1",
    "驳": "bo2",
    "崽": "zai3",
    "焉": "yan1",
    "窜": "cuan4",
    "黏": "nian2",
    "亦": "yi4",
    "届": "jie4",
    # Approved SUBTLEX-CH top-2300 character expansion, 2026-10-06.
    "铐": "kao4",
    "辨": "bian4",
    "荐": "jian4",
    "均": "jun1",
    "矛": "mao2",
    "峰": "feng1",
    "鸭": "ya1",
    "庞": "pang2",
    "饱": "bao3",
    "囊": "nang2 / nang1",
    "剥": "bao1 / bo1",
    "紫": "zi3",
    "妄": "wang4",
    "膏": "gao1 / gao4",
    "筋": "jin1",
    "浅": "qian3",
    "勋": "xun1",
    "夷": "yi2",
    "橱": "chu2",
    "兆": "zhao4",
    "畏": "wei4",
    "寂": "ji4",
    "鹅": "e2",
    "疚": "jiu4",
    "缸": "gang1",
    "陶": "tao2",
    "浆": "jiang1 / jiang4",
    "讼": "song4",
    "穴": "xue2",
    "玫": "mei2",
    "捣": "dao3",
    "奎": "kui2",
    "赤": "chi4",
    "脂": "zhi1",
    "瑰": "gui1",
    "垮": "kua3",
    "饶": "rao2",
    "疤": "ba1",
    "琪": "qi2",
    "篷": "peng2",
    "猩": "xing1",
    "靴": "xue1",
    "涯": "ya2",
    "桩": "zhuang1",
    "钩": "gou1",
    "苍": "cang1",
    "寿": "shou4",
    "缉": "ji1 / qi1",
    "酬": "chou2",
    "碟": "die2",
    "促": "cu4",
    "畜": "chu4 / xu4",
    "纱": "sha1",
    "悦": "yue4",
    "循": "xun2",
    "烛": "zhu2",
    "览": "lan3",
    "堕": "duo4",
    "棋": "qi2",
    "贡": "gong4",
    "券": "quan4",
    "艳": "yan4",
    "卜": "bu3 / bo5",
    "膜": "mo2",
    "珀": "po4",
    "藤": "teng2",
    "肮": "ang1",
    "斑": "ban1",
    "徽": "hui1",
    "综": "zong1 / zeng4",
    "劣": "lie4",
    "珊": "shan1",
    "跨": "kua4",
    "扁": "bian3 / pian1",
    "妳": "ni3",
    "携": "xie2",
    "痒": "yang3",
    "粒": "li4",
    "呕": "ou3 / ou4 / ou1",
    "跌": "die1",
    "坟": "fen2",
    "贞": "zhen1",
    "镑": "bang4",
    "罕": "han3",
    "狐": "hu2",
    "阅": "yue4",
    "钞": "chao1",
    "镖": "biao1",
    "敞": "chang3",
    "棵": "ke1",
    "肢": "zhi1",
    "咙": "long2",
    "匿": "ni4",
    "饥": "ji1",
    "薇": "wei1",
    "宅": "zhai2",
    "棺": "guan1",
    "腺": "xian4",
    "岗": "gang3 / gang1",
    "刊": "kan1",
    "柴": "chai2",
    "橡": "xiang4",
    "淇": "qi2",
    "阱": "jing3",
    "贿": "hui4",
    "捅": "tong3",
    "棉": "mian2",
    "翅": "chi4",
    "贤": "xian2",
    "淹": "yan1",
    "龟": "gui1 / jun1 / qiu1",
    "榜": "bang3",
    "喻": "yu4",
    "澳": "ao4",
    "泼": "po1",
    "拟": "ni3",
    "椒": "jiao1",
    "扳": "ban1",
    "舅": "jiu4",
    "咨": "zi1",
    "莓": "mei2",
    "盆": "pen2",
    "懦": "nuo4",
    "碧": "bi4",
    "颈": "jing3 / geng3",
    "後": "hou4",
    "焰": "yan4",
    "乃": "nai3",
    "钮": "niu3",
    "泣": "qi4",
    "熏": "xun1 / xun4",
    "岳": "yue4",
    "咔": "ka1 / ka3",
    "帖": "tie3 / tie4 / tie1",
    "咋": "za3 / zha1",
    "虾": "xia1",
    "爪": "zhua3 / zhao3",
    "桓": "huan2",
    "哑": "ya3 / ya1",
    "雀": "que4",
    "粥": "zhou1",
    "咳": "ke2 / hai1",
}

MANUAL_ENTRIES: dict[str, tuple[str, str]] = {
    # Second user-selected vocabulary batch, 2026-10-19.
    "屏住": ("bing3 zhu4", "to hold back; to hold (one's breath)"),
    "本次": ("ben3 ci4", "this time; this occasion; this current event"),
    # User-selected vocabulary additions, 2026-10-19.
    "丝毫": ("si1 hao2", "the slightest amount; a bit (usually with a negative)"),
    "结实": ("jie1 shi5", "sturdy; strong; durable"),
    "宠物": ("chong3 wu4", "pet; companion animal"),
    "鞠躬": ("ju1 gong1", "to bow"),
    "游走": ("you2 zou3", "to roam; to move about or between places"),
    "草丛": ("cao3 cong2", "clump of grass; undergrowth"),
    "边缘": ("bian1 yuan2", "edge; fringe; periphery"),
    "小心翼翼": ("xiao3 xin1 yi4 yi4", "very carefully; cautiously"),
    "嘟囔": ("du1 nang5", "to mutter; to mumble to oneself"),
    "嫌弃": ("xian2 qi4", "to dislike or reject with disdain; to look down on"),
    "以上": ("yi3 shang4", "above; or more; the above-mentioned"),
    "发育": ("fa1 yu4", "to grow and develop; to mature; to build strength (in games)"),
    "闪烁": ("shan3 shuo4", "to flicker; to sparkle; to twinkle"),
    "好歹": ("hao3 dai3", "good and bad; at least; in any case"),
    "退役": ("tui4 yi4", "to retire from sport or military service; to decommission"),
    "联赛": ("lian2 sai4", "sports league; league competition"),
    "元素": ("yuan2 su4", "element; component"),
    "拉扯": ("la1 che5", "to pull or tug; to bring up a child with difficulty"),
    "提示": ("ti2 shi4", "hint; prompt; reminder; to point out"),
    "后排": ("hou4 pai2", "back row; rear seats"),
    "点燃": ("dian3 ran2", "to light; to ignite; to kindle"),
    "摄影": ("she4 ying3", "photography; to photograph or film"),
    "抽签": ("chou1 qian1", "to draw lots"),
    "胡萝卜": ("hu2 luo2 bo5", "carrot"),
    "替补": ("ti4 bu3", "substitute; replacement; to substitute"),
    "观众席": ("guan1 zhong4 xi2", "audience seating; spectator stands"),
    "媳妇": ("xi2 fu5 / xi2 fu4", "wife (xi2 fu5, colloquial); daughter-in-law (xi2 fu4)"),
    "理所当然": ("li3 suo3 dang1 ran2", "natural and right; to be expected; as a matter of course"),
    "开幕": ("kai1 mu4", "to open; opening of an event"),
    "一幕": ("yi2 mu4", "a scene; an act of a play"),
    "节奏": ("jie2 zou4", "rhythm; tempo; pace"),
    "逐渐": ("zhu2 jian4", "gradually; little by little"),
    "名额": ("ming2 e2", "place; slot; quota"),
    "过于": ("guo4 yu2", "too; excessively"),
    "灵活": ("ling2 huo2", "flexible; nimble; agile"),
    "质疑": ("zhi4 yi2", "to question; to challenge the validity of"),
    "版本": ("ban3 ben3", "version; edition"),
    "总结": ("zong3 jie2", "to summarize; to sum up; summary"),
    "如今": ("ru2 jin1", "now; nowadays"),
    "落后": ("luo4 hou4", "to fall behind; to lag; behind; backward"),
    "复活": ("fu4 huo2", "to come back to life; to revive; to respawn in a game"),
    "握手": ("wo4 shou3", "to shake hands"),
    "爆发": ("bao4 fa1", "to break out; to erupt; to burst out"),
    "占据": ("zhan4 ju4", "to occupy; to take up; to hold"),
    "素质": ("su4 zhi4", "personal qualities; competence; manners; basic capacity"),
    "官方": ("guan1 fang1", "official; the authorities"),
    "正面": ("zheng4 mian4", "front; facing forward; direct; positive"),
    "当前": ("dang1 qian2", "current; present; at present"),
    # User-selected Falling Into Your Smile characters, 2026-10-17.
    "嗖": ("sou1", "whoosh; swish (sound)"),
    "嘶": ("si1", "to hiss; to neigh; hoarse (in compounds)"),
    "扒": ("ba1 / pa2", "to pull apart; to peel (ba1); to rake; to steal (pa2)"),
    "咕": ("gu1", "cooing; gurgling; rumbling (sound)"),
    "僧": ("seng1", "Buddhist monk"),
    "嗅": ("xiu4", "to smell; to sniff"),
    "烁": ("shuo4", "bright; shining; to sparkle (in compounds)"),
    "躬": ("gong1", "body; to bow; personally (literary)"),
    "鞠": ("ju1", "to bow; to raise or nurture (literary)"),
    "撩": ("liao1 / liao2", "to lift up (liao1); to tease; to flirt with (liao2)"),
    "芒": ("mang2", "awn of grain; sharp tip; ray of light (in compounds)"),
    "颊": ("jia2", "cheek"),
    "宵": ("xiao1", "night"),
    "岚": ("lan2", "mountain mist"),
    "峡": ("xia2", "gorge; canyon"),
    "搓": ("cuo1", "to rub or roll between the hands"),
    "撇": ("pie1 / pie3", "to cast aside (pie1); to curl the lips; left-falling written stroke (pie3)"),
    "歹": ("dai3", "bad; evil; wicked"),
    "萌": ("meng2", "to sprout; to bud; cute; adorable"),
    "踮": ("dian3", "to stand on tiptoe"),
    "凳": ("deng4", "stool; bench"),
    "嗳": ("ai3 / ai4", "hey; no (ai3, disapproval); oh (ai4, regret); to belch (ai3)"),
    "戳": ("chuo1", "to poke; to jab; stamp; seal"),
    "敛": ("lian3", "to gather; to restrain; to hold back"),
    "耸": ("song3", "to shrug; to raise; to tower"),
    "蹿": ("cuan1", "to leap up; to dart; to spurt out"),
    "捶": ("chui2", "to beat; to pound with a fist or stick"),
    "狸": ("li2", "character in names of small mammals, such as 狐狸 (fox)"),
    "砰": ("peng1", "bang; thump (sound)"),
    "伐": ("fa2", "to fell; to cut down; to attack"),
    "喵": ("miao1", "meow (a cat's sound)"),
    "噜": ("lu1", "rumbling or murmuring sound (in compounds)"),
    "腻": ("ni4", "greasy; rich; tired of; bored with"),
    "译": ("yi4", "to translate; to interpret"),
    "漉": ("lu4", "to strain liquid; wet (in 湿漉漉)"),
    "绵": ("mian2", "soft; continuous; silk floss"),
    "赅": ("gai1", "complete; comprehensive; concise (in 言简意赅)"),
    "颚": ("e4", "jaw"),
    "叼": ("diao1", "to hold in the mouth or between the teeth"),
    "叽": ("ji1", "chirping; chattering (sound)"),
    "咸": ("xian2", "salty; all (literary)"),
    "扛": ("kang2 / gang1", "to carry on the shoulder (kang2); to lift with both hands (gang1)"),
    "揪": ("jiu1", "to grab firmly; to clutch; to tug"),
    "涨": ("zhang3 / zhang4", "to rise, of prices or water (zhang3); to swell (zhang4)"),
    "猝": ("cu4", "suddenly; abruptly; unexpectedly"),
    "膛": ("tang2", "chest; hollow chamber or cavity"),
    "晰": ("xi1", "clear; distinct"),
    "曜": ("yao4", "to shine; bright; a celestial luminary; used in personal names"),
    "衩": ("cha3 / cha4", "part of 裤衩, shorts or underpants (cha3); slit in a garment (cha4)"),
    "巅": ("dian1", "summit; peak"),
    "揣": ("chuai1 / chuai3", "to put inside clothes or a pocket (chuai1); to guess; to estimate (chuai3)"),
    "吁": ("xu1 / yu4", "to sigh; to exhale (xu1); to appeal; to call for (yu4)"),
    "葱": ("cong1", "scallion; green onion"),
    "驳": ("bo2", "to refute; to contradict; mottled"),
    "崽": ("zai3", "young animal; child (colloquial)"),
    "焉": ("yan1", "where; how; there; literary particle"),
    "窜": ("cuan4", "to flee; to scurry; to dart"),
    "黏": ("nian2", "sticky; glutinous"),
    "亦": ("yi4", "also; too (literary)"),
    "届": ("jie4", "term; session; measure word for events or graduating classes"),
    # Approved SUBTLEX-CH top-2300 character expansion, 2026-10-06.
    "铐": ("kao4", "handcuffs; to handcuff"),
    "辨": ("bian4", "to distinguish; to tell apart"),
    "荐": ("jian4", "to recommend"),
    "均": ("jun1", "equal; even; all"),
    "矛": ("mao2", "spear; lance"),
    "峰": ("feng1", "mountain peak; highest point"),
    "鸭": ("ya1", "duck"),
    "庞": ("pang2", "huge; enormous"),
    "饱": ("bao3", "full from eating; satisfied"),
    "囊": ("nang2 / nang1", "bag; sac; capsule (nang2); soft or mushy (nang1)"),
    "剥": ("bao1 / bo1", "to peel or shell (bao1); to strip off (bo1)"),
    "紫": ("zi3", "purple; violet"),
    "妄": ("wang4", "reckless; absurd; presumptuous"),
    "膏": ("gao1 / gao4", "paste; ointment (gao1); to lubricate (gao4)"),
    "筋": ("jin1", "tendon; sinew; muscle (in compounds)"),
    "浅": ("qian3", "shallow; light in color; superficial"),
    "勋": ("xun1", "merit; distinguished service"),
    "夷": ("yi2", "level; to flatten; foreign peoples (historical)"),
    "橱": ("chu2", "cupboard; cabinet"),
    "兆": ("zhao4", "sign; omen; million (mega-); trillion in some counting systems"),
    "畏": ("wei4", "to fear; to hold in awe"),
    "寂": ("ji4", "quiet; still; lonely"),
    "鹅": ("e2", "goose"),
    "疚": ("jiu4", "guilt; remorse"),
    "缸": ("gang1", "vat; jar; tank"),
    "陶": ("tao2", "pottery; ceramics; to cultivate or delight (in compounds)"),
    "浆": ("jiang1 / jiang4", "thick liquid; pulp; starch (jiang1); thick or pasty (jiang4)"),
    "讼": ("song4", "litigation; lawsuit"),
    "穴": ("xue2", "cave; hole; den"),
    "玫": ("mei2", "part of 玫瑰, rose"),
    "捣": ("dao3", "to pound; to mash; to make trouble (in compounds)"),
    "奎": ("kui2", "name of a traditional Chinese constellation; used in personal names"),
    "赤": ("chi4", "red; bare; naked"),
    "脂": ("zhi1", "fat; grease"),
    "瑰": ("gui1", "precious; extraordinary; part of 玫瑰, rose"),
    "垮": ("kua3", "to collapse; to break down"),
    "饶": ("rao2", "to spare; to forgive; abundant"),
    "疤": ("ba1", "scar"),
    "琪": ("qi2", "fine jade; used in personal names"),
    "篷": ("peng2", "awning; canopy; tent covering"),
    "猩": ("xing1", "part of 猩猩, ape, and 猩红, scarlet"),
    "靴": ("xue1", "boot"),
    "涯": ("ya2", "water's edge; limit; span (in compounds)"),
    "桩": ("zhuang1", "stake; post; measure word for cases or matters"),
    "钩": ("gou1", "hook; to hook"),
    "苍": ("cang1", "gray; pale; dark green or blue"),
    "寿": ("shou4", "long life; lifespan"),
    "缉": ("ji1 / qi1", "to arrest or track down (ji1); to stitch closely (qi1)"),
    "酬": ("chou2", "payment; reward; to repay"),
    "碟": ("die2", "small plate; saucer; disc"),
    "促": ("cu4", "to urge; to promote; hurried"),
    "畜": ("chu4 / xu4", "livestock; beast (chu4); to raise livestock (xu4)"),
    "纱": ("sha1", "yarn; gauze; thin fabric"),
    "悦": ("yue4", "pleased; delighted; to please"),
    "循": ("xun2", "to follow; to comply with"),
    "烛": ("zhu2", "candle"),
    "览": ("lan3", "to view; to look over"),
    "堕": ("duo4", "to fall; to sink; to degenerate"),
    "棋": ("qi2", "chess or other board games; game piece"),
    "贡": ("gong4", "tribute; to contribute"),
    "券": ("quan4", "ticket; voucher; certificate"),
    "艳": ("yan4", "bright-colored; gorgeous"),
    "卜": ("bu3 / bo5", "to divine; to predict (bu3); part of 萝卜, radish (bo5)"),
    "膜": ("mo2", "membrane; thin film"),
    "珀": ("po4", "part of 琥珀, amber"),
    "藤": ("teng2", "vine; rattan"),
    "肮": ("ang1", "dirty; filthy (in 肮脏)"),
    "斑": ("ban1", "spot; stripe; patch"),
    "徽": ("hui1", "badge; emblem"),
    "综": ("zong1 / zeng4", "to sum up; comprehensive (zong1); heddle (zeng4, weaving)"),
    "劣": ("lie4", "inferior; poor; bad"),
    "珊": ("shan1", "part of 珊瑚, coral"),
    "跨": ("kua4", "to stride across; to span"),
    "扁": ("bian3 / pian1", "flat (bian3); small (pian1, in 扁舟)"),
    "妳": ("ni3", "you (feminine written form of 你)"),
    "携": ("xie2", "to carry; to take along"),
    "痒": ("yang3", "itchy; to itch"),
    "粒": ("li4", "grain; small particle; measure word for small round things"),
    "呕": ("ou3 / ou4 / ou1", "to vomit (ou3); to annoy (ou4); to sing (ou1, literary)"),
    "跌": ("die1", "to fall; to tumble; to drop in value"),
    "坟": ("fen2", "grave; tomb"),
    "贞": ("zhen1", "steadfast; faithful; chaste"),
    "镑": ("bang4", "pound sterling"),
    "罕": ("han3", "rare; uncommon"),
    "狐": ("hu2", "fox"),
    "阅": ("yue4", "to read; to inspect"),
    "钞": ("chao1", "paper money; banknote; to copy (literary)"),
    "镖": ("biao1", "dart; throwing weapon; escorted goods (historical)"),
    "敞": ("chang3", "open; spacious"),
    "棵": ("ke1", "measure word for trees and plants"),
    "肢": ("zhi1", "limb"),
    "咙": ("long2", "part of 喉咙, throat"),
    "匿": ("ni4", "to hide; to conceal"),
    "饥": ("ji1", "hungry; hunger; famine"),
    "薇": ("wei1", "a plant name; part of 蔷薇, rose; used in personal names"),
    "宅": ("zhai2", "residence; house; to stay at home"),
    "棺": ("guan1", "coffin"),
    "腺": ("xian4", "gland"),
    "岗": ("gang3 / gang1", "post; position (gang3); low hill (gang1)"),
    "刊": ("kan1", "publication; to publish; to print"),
    "柴": ("chai2", "firewood"),
    "橡": ("xiang4", "oak; rubber (in 橡胶)"),
    "淇": ("qi2", "name of the Qi River; used in personal names"),
    "阱": ("jing3", "trap; pitfall"),
    "贿": ("hui4", "bribe; to bribe"),
    "捅": ("tong3", "to poke; to jab; to pierce"),
    "棉": ("mian2", "cotton"),
    "翅": ("chi4", "wing"),
    "贤": ("xian2", "worthy; virtuous; capable"),
    "淹": ("yan1", "to flood; to submerge; to drown"),
    "龟": ("gui1 / jun1 / qiu1", "turtle (gui1); cracked (jun1, in 龟裂); Qiu (qiu1, in place names)"),
    "榜": ("bang3", "list; ranking; notice board"),
    "喻": ("yu4", "to explain; to understand; analogy (in 比喻)"),
    "澳": ("ao4", "bay; inlet; short for Australia or Macao in compounds"),
    "泼": ("po1", "to splash; to spill; lively (in 活泼)"),
    "拟": ("ni3", "to draft; to plan; to imitate"),
    "椒": ("jiao1", "pepper (in compounds)"),
    "扳": ("ban1", "to pull or turn; to reverse a situation"),
    "舅": ("jiu4", "maternal uncle; wife's brother"),
    "咨": ("zi1", "to consult; to ask for advice"),
    "莓": ("mei2", "berry (in compounds)"),
    "盆": ("pen2", "basin; tub; pot"),
    "懦": ("nuo4", "cowardly; weak"),
    "碧": ("bi4", "jade green; blue-green"),
    "颈": ("jing3 / geng3", "neck (jing3; geng3 in 脖颈儿)"),
    "後": ("hou4", "after; behind; later (traditional form of 后)"),
    "焰": ("yan4", "flame; blaze"),
    "乃": ("nai3", "to be; therefore; only then (literary)"),
    "钮": ("niu3", "button; knob"),
    "泣": ("qi4", "to weep; to sob"),
    "熏": ("xun1 / xun4", "to smoke; to fumigate (xun1); to choke with fumes (xun4)"),
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
    "帮帮": ("bang1 bang1", "to help; to give someone a hand (reduplicated form)"),
    "汤米": ("tang1 mi3", "Tommy (person name)"),
    "镇上": ("zhen4 shang4", "in town; in the town"),
    "我家": ("wo3 jia1", "my home; my family"),
    "小姑娘": ("xiao3 gu1 niang5", "young girl; young woman"),
    "放到": ("fang4 dao4", "to put or place in, on, or at"),
    "好样": ("hao3 yang4", "admirable; worthy of praise (usually 好样的)"),
    "第六": ("di4 liu4", "sixth"),
    "迈克": ("mai4 ke4", "Mike (person name)"),
    "其他人": ("qi2 ta1 ren2", "other people; everyone else"),
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


def read_words(path: Path = WORD_LIST) -> list[str]:
    words: list[str] = []
    first_line_by_word: dict[str, int] = {}
    duplicates: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        word = line.strip()
        if not word:
            continue
        if word in first_line_by_word:
            duplicates.append(
                f"{word!r} on lines {first_line_by_word[word]} and {line_number}"
            )
            continue
        words.append(word)
        first_line_by_word[word] = line_number

    if duplicates:
        raise RuntimeError(
            f"Duplicate words in {path}: " + "; ".join(duplicates[:20])
        )
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

        pinyin = WORD_PINYIN_OVERRIDES.get(word, pinyin)
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
