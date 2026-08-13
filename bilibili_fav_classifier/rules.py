"""Category and tag classification rules.

Bilibili assigns each video an official partition (tname) and user-added tags.
These are more reliable signals than title keywords alone.
"""
from __future__ import annotations

import re

# ── Bilibili official partition (tname) → folder mapping ────────────
# Full list of Bilibili partitions: https://www.bilibili.com/blackboard/blackroom.html

PARTITION_RULES: dict[str, str] = {
    # 科技区
    "科技": "AI与编程技术",
    "数码": "汽车·数码",
    "软件应用": "AI与编程技术",
    # 知识区
    "知识": "学习与竞赛",
    "科学科普": "生活与社会",
    "社科·法律·心理": "学习与竞赛",
    "人文历史": "历史与时政",
    "商业": "财经商业",
    "财经": "财经商业",
    # 游戏区
    "游戏": "游戏与动漫",
    "单机游戏": "游戏与动漫",
    "电子竞技": "游戏与动漫",
    "手机游戏": "游戏与动漫",
    "网络游戏": "游戏与动漫",
    # 娱乐区
    "娱乐": "生活与社会",
    "综艺": "生活与社会",
    "明星": "生活与社会",
    # 生活区
    "生活": "生活与社会",
    "日常": "生活与社会",
    "美食": "生活与社会",
    "动物圈": "宠物生活",
    "汽车": "汽车·数码",
    "家居": "生活与社会",
    "家居·房产": "生活与社会",
    # 运动区
    "运动": "体育",
    "健身": "体育",
    "篮球": "体育",
    "足球": "体育",
    "羽毛球": "体育",
    "乒乓球": "体育",
    "游泳": "体育",
    "台球": "体育",
    "搏击": "体育",
    # 音乐区
    "音乐": "音乐",
    "翻唱": "音乐",
    "演奏": "音乐",
    "VOCALOID·UTAU": "音乐",
    "音乐现场": "音乐",
    # 舞蹈区
    "舞蹈": "生活与社会",
    # 影视区
    "影视": "生活与社会",
    "电影": "生活与社会",
    "电视剧": "生活与社会",
    "纪录片": "生活与社会",
    # 时尚区
    "时尚": "生活与社会",
    "美妆": "生活与社会",
    "穿搭": "生活与社会",
    # 动漫区（番剧/国创/动画及其子分区）
    "动画": "游戏与动漫",
    "番剧": "游戏与动漫",
    "国创": "游戏与动漫",
    "国创相关": "游戏与动漫",
    "MAD·AMV": "游戏与动漫",
    "MMD·3D": "游戏与动漫",
    "手书·短片": "游戏与动漫",
    "同人": "游戏与动漫",
    "综合": "游戏与动漫",
    "音游": "游戏与动漫",
    # 影视延伸 / 资讯 / 鬼畜
    "影视相关": "生活与社会",
    "影视杂谈": "生活与社会",
    "影视剪辑": "生活与社会",
    "小剧场": "生活与社会",
    "资讯": "生活与社会",
    "鬼畜": "生活与社会",
    # 动物圈（已在上面）
    # 汽车（已在上面）
}


# ── User-added video tags → folder mapping ──────────────────────────
# Lowercase substrings matched against tag text.
# Each entry: (slash-separated keywords, folder_name)

TAG_RULES: list[tuple[str, str]] = [
    # AI & Programming
    ("编程/python/java/c++/代码/算法/claude/cursor/coze/agent/前端/后端/框架/开发/软件/程序员/vscode/git/docker/api/github/linux/debug/开源/人工智能/machine learning/deep learning/神经网络/大模型/llm/rag/chatgpt/gpt/deepseek/transformer/微调/finetune/rag/爬虫/后端/前端/react/vue/node/typescript/rust/golang/openai", "AI与编程技术"),
    # Learning
    ("考研/数学/物理/化学/生物/英语/四级/六级/cet/雅思/托福/论文/科研/sci/竞赛/acm/蓝桥杯/数模/期末/复习/课件/经管/高数/线代/概率/离散/专业课/大学/课程/读书/阅读/书籍/书评/文学/哲学/公开课/ted", "学习与竞赛"),
    # Gaming & Anime
    ("游戏/gta/原神/三角洲/我的世界/实况/攻略/steam/塞尔达/黑神话/王者/和平精英/lol/csgo/mc/通关/原神/崩坏/星穹铁道/明日方舟/幻塔/鸣潮/抽卡/练度/pawn/游戏评测/主机/switch/ps5/xbox/apex/瓦罗兰特/永劫无间/暗区突围/蛋仔派对", "游戏与动漫"),
    ("动漫/新番/番剧/鬼灭/咒术/进击的巨人/间谍过家家/鬼畜/名场面/整活/二创/mad/amv/间谍/海贼/火影/死神/柯南/鬼灭/咒术/电锯人/间谍过家家/我推的孩子/葬送的芙莉莲/咒术回战", "游戏与动漫"),
    ("Minecraft/我的世界/生存/建筑", "游戏与动漫"),
    # Sports
    ("健身/跑步/减肥/运动/keep/肌肉/拉伸/瑜伽/马拉松/篮球/足球/乒乓/羽毛球/网球/游泳/骑行/街健/滑雪/冲浪/攀岩/拳击/散打/太极/八段锦", "体育"),
    # Music
    ("音乐/翻唱/钢琴/吉他/古筝/日文歌/歌词/歌曲/演唱/mv/bgm/纯音乐/乐理/作曲/编曲/乐队/摇滚/民谣/说唱/rap/电音/edm/古风/戏腔/二胡/小提琴/大提琴/架子鼓", "音乐"),
    # Emotion & Copywriting
    ("情感/文案/治愈/感悟/人生/爱情/故事/遗憾/告别/emo/伤感/心理/情商/社交/人际关系/树洞/emo/抑郁/焦虑/成长/心灵/鸡汤", "情感与文案"),
    # History & Politics
    ("历史/二战/苏联/蒋介石/国民党/近代史/朝代/时政/国际/俄乌/特朗普/地缘/资本家/政治/战争/革命/民国/清朝/明朝/唐朝/宋朝/明朝那些事儿/抗日战争/抗美援朝", "历史与时政"),
    # Finance & Business
    ("财经/股票/基金/理财/投资/比特币/btc/eth/纳斯达克/a股/港股/美股/上市/财报/经济/金融/宏观经济/微观经济/贸易战/物价/房价/存款/利率/央行/美联储", "财经商业"),
    ("副业/创业/开店/商业模式/赚钱/收入/成本/利润/供应链/电商/淘宝/京东/拼多多/跨境电商/自媒体/流量/变现/抖音/小红书", "财经商业"),
    # Career & Growth
    ("职场/工作/面试/简历/升职/自我提升/自律/效率/时间管理/笔记法/考研/考公/考编/体制/公务员/国企/大厂/裁员/996/加班/领导力/管理/团队", "职场成长"),
    ("自律/习惯/早起/冥想/读书笔记/复盘/目标管理/精力管理/深度工作/认知升级/思维模型/第一性原理", "职场成长"),
    # Parenting
    ("育儿/母婴/宝宝/怀孕/早教/胎教/辅食/产后/新生儿/坐月子/催产/学区房/奶粉/纸尿裤/亲子/胎动/顺产/剖腹产", "母婴育儿"),
    ("婴儿/幼儿/儿童/小学生/初中生/高中生/青春期/叛逆期/学区/奥数/兴趣班/钢琴/舞蹈/画画/编程启蒙", "母婴育儿"),
    # Pets
    ("猫/狗/宠物/养猫/养狗/猫粮/狗粮/猫砂/猫砂盆/猫爬架/绝育/疫苗/驱虫/流浪猫/流浪狗/救助/撸猫/撸狗/拆家/哈士奇/柯基/布偶猫/英短", "宠物生活"),
    # Life & Society (broad catch-all)
    ("美食/做饭/食谱/探店/深夜食堂/厨师/烘焙/家常菜/下厨房/美食制作", "生活与社会"),
    ("旅行/生活/日常/vlog/大学生/毕业/职场/社畜/租房/独居/留学/移民/出国/签证/留学申请", "生活与社会"),
    ("科普/知识/冷知识/科学/物理/化学/天文/地理/自然/医学/健康/养生/中医/西医/疫苗/体检/体检报告", "生活与社会"),
    ("影视/电影/解说/影评/纪录片/netflix/奥斯卡/豆瓣/票房/烂片/神作/推荐/剧情分析", "生活与社会"),
    ("汽车/测评/手机/电脑/硬件/iphone/小米/华为/苹果/显卡/笔记本/耳机/平板/智能手表/折叠屏", "汽车·数码"),
    ("搞笑/整活/沙雕/离谱/绷不住/笑点/段子/喜剧/整活/迷惑行为", "生活与社会"),
    ("vlog/日常/记录/生活记录/plog/weekly vlog", "生活与社会"),
    ("装修/设计/室内/家居/北欧风/日式/装修日记/全屋定制", "生活与社会"),
    ("手工/diy/crafts/折纸/陶艺/木工/手作/串珠/编织/刺绣/奶油胶", "生活与社会"),
    ("摄影/拍照/相机/镜头/佳能/索尼/富士/尼康/拍立得/胶片/调色/后期/ps/lr/修图", "生活与社会"),
    ("三农/农村/种田/养殖/赶海/捕鱼/种菜/养鸡/养鸭/新农村/乡村振兴", "生活与社会"),
    ("穿搭/衣服/时尚/化妆/美妆/护肤/面膜/口红/眼影/粉底/olay/雅诗兰黛/兰蔻/skii", "生活与社会"),
    ("租房/买房/装修/房贷/公积金/不动产/学区房/落户/户口/社保/医保/五险一金", "生活与社会"),
]


# ── Title keyword rules (fallback layer) ─────────────────────────────
# Applied when tags and partition don't match.
# Each entry: (slash-separated keywords, folder_name)

KEYWORD_RULES: list[tuple[str, str]] = [
    # AI & Programming
    (
        "编程/开发/技术/AI/代码/算法/Claude/Cursor/Coze/Agent"
        "/Python/Java/C++/前端/后端/框架/引擎/软件/程序"
        "/VSCode/Git/Linux/Docker/API/GitHub/程序员"
        "/深度学习/机器学习/神经网络/大模型/LLM/RAG"
        "/ChatGPT/GPT/DeepSeek/爬虫/React/Vue/Node/Rust/Golang/Go语言/OpenAI",
        "AI与编程技术",
    ),
    # Learning
    (
        "算法/竞赛/ACM/蓝桥杯/数模/建模/数学/高数/线代/概率"
        "/论文/科研/SCI/英语/四级/六级/CET/雅思/托福"
        "/考研/期末/复习/课件/物理/化学/生物/经管"
        "/公开课/TED/读书/书籍/文学/哲学/大学/课程",
        "学习与竞赛",
    ),
    # Gaming & Anime
    (
        "游戏/GTA/原神/三角洲/我的世界/实况/攻略/Steam"
        "/塞尔达/黑神话/王者/和平精英/LOL/CSGO/MC"
        "/原神/崩坏/星穹铁道/明日方舟/幻塔/鸣潮"
        "/新番/番剧/鬼灭/咒术/巨人/动漫/鬼畜/二创/MAD/AMV",
        "游戏与动漫",
    ),
    # Sports
    ("健身/跑步/减肥/运动/KEEP/肌肉/拉伸/瑜伽/篮球/足球/乒乓/游泳/骑行/街健/马拉松/滑雪", "体育"),
    # Music
    (
        "音乐/翻唱/钢琴/吉他/古筝/日文歌/歌词/NIGHT DANCER"
        "/歌曲/演唱/MV/BGM/纯音乐/乐理/作曲/编曲/乐队/摇滚/民谣/说唱/RAP",
        "音乐",
    ),
    # Emotion & Copywriting
    (
        "情感/文案/治愈/感悟/人生/爱情/故事/遗憾/告别"
        "/EMO/伤感/心理/情商/社交/树洞/鸡汤/emo/抑郁",
        "情感与文案",
    ),
    # History & Politics
    (
        "历史/二战/苏联/蒋介石/国民党/近代史/朝代"
        "/时政/国际/俄乌/特朗普/访华/地缘政治/资本家"
        "/清朝/明朝/唐朝/宋朝/抗日战争/抗美援朝",
        "历史与时政",
    ),
    # Finance & Business
    (
        "财经/股票/基金/理财/投资/比特币/BTC/ETH/纳斯达克"
        "/A股/港股/美股/上市/财报/经济/金融/宏观经济/物价/房价"
        "/存款/利率/央行/美联储/副业/创业/开店/商业模式"
        "/赚钱/电商/淘宝/京东/自媒体/流量/变现",
        "财经商业",
    ),
    # Career & Growth
    (
        "职场/工作/面试/简历/升职/自我提升/自律/效率/时间管理"
        "/考公/考编/体制/公务员/国企/大厂/裁员/996/加班"
        "/领导力/管理/团队/复盘/目标管理/精力管理/认知升级"
        "/笔记法/深度工作/思维模型",
        "职场成长",
    ),
    # Parenting
    (
        "育儿/母婴/宝宝/怀孕/早教/胎教/辅食/产后/新生儿"
        "/坐月子/学区房/奶粉/纸尿裤/亲子/胎动/顺产/剖腹产"
        "/婴儿/幼儿/儿童/小学生/初中生/青春期/叛逆期"
        "/奥数/兴趣班/钢琴启蒙/舞蹈启蒙/画画/编程启蒙",
        "母婴育儿",
    ),
    # Pets
    (
        "猫/狗/宠物/养猫/养狗/猫粮/狗粮/猫砂/猫砂盆/绝育/疫苗"
        "/驱虫/流浪猫/流浪狗/救助/撸猫/撸狗/拆家"
        "/哈士奇/柯基/布偶猫/英短/美短/暹罗猫/金毛/拉布拉多",
        "宠物生活",
    ),
    # Life & Society
    (
        "美食/做饭/食谱/探店/深夜食堂/厨师/烘焙/家常菜/下厨房"
        "/旅行/生活/日常/Vlog/大学生/毕业/职场/社畜/租房/独居"
        "/科普/知识/冷知识/科学/物理/化学/天文/地理/自然"
        "/医学/健康/养生/中医/疫苗/体检/纪录片"
        "/影视/电影/解说/影评/Netflix/奥斯卡/豆瓣/票房"
        "/汽车/测评/手机/电脑/硬件/iPhone/小米/华为/苹果/显卡/笔记本/耳机"
        "/搞笑/整活/沙雕/离谱/绷不住/笑点/段子/喜剧"
        "/vlog/日常/记录/生活记录/plog"
        "/装修/设计/室内/家居/北欧风/装修日记"
        "/手工/diy/crafts/折纸/陶艺/木工/手作"
        "/摄影/拍照/相机/镜头/佳能/索尼/富士/调色/修图"
        "/三农/农村/种田/养殖/赶海/捕鱼/新农村"
        "/穿搭/衣服/时尚/化妆/美妆/护肤/面膜/口红/眼影"
        "/买房/房贷/公积金/落户/社保/医保",
        "生活与社会",
    ),
]


# ──────────────────────── Matching functions ────────────────────────


def _boundary_check(text: str, kw: str) -> bool:
    """Word boundary check: use word boundary for pure English inputs,
    substring match for Chinese-containing inputs (since \b doesn't work well at Chinese/English boundaries).
    """
    # If input text contains non-ASCII characters (Chinese), use substring match
    # because word boundary \b doesn't work well at Chinese/English boundaries
    if any(ord(c) > 127 for c in text):
        return kw in text
    # Pure English input: use word boundary to avoid false positives
    if not any(ord(c) > 127 for c in kw):
        pattern = rf"\b{re.escape(kw)}\b"
        return bool(re.search(pattern, text))
    # Mixed case: fallback to substring (shouldn't happen in practice)
    return kw in text


def normalize_tags(tags: list[str] | str | None) -> list[str]:
    """Normalize tag input: accept list or comma-separated string.

    B站 fav list API returns tags as comma-separated string.
    After enrich, tags become list. This function handles both.
    """
    if not tags:
        return []
    if isinstance(tags, str):
        if not tags.strip():
            return []
        # Comma-separated string -> list
        return [t.strip() for t in tags.split(",") if t.strip()]
    return list(tags)


def partition_match(tname: str | None) -> str | None:
    """Match Bilibili partition name to a folder."""
    if not tname:
        return None
    return PARTITION_RULES.get(tname)


def tag_match(tags: list[str] | str | None) -> str | None:
    """Match user-added tags to a folder (first match wins).

    Accepts list or comma-separated string (defensive against API format).
    """
    normalized = normalize_tags(tags)
    if not normalized:
        return None
    tag_str = " ".join(t.lower() for t in normalized)
    for rule_str, folder in TAG_RULES:
        for kw in rule_str.split("/"):
            if _boundary_check(tag_str, kw.lower()):
                return folder
    return None


def keyword_classify(title: str) -> str | None:
    """Match title keywords to a folder (first match wins).

    Uses word boundary for ASCII keywords to avoid false positives
    (e.g., 'go' in 'good' or 'ai' in 'again').
    """
    t = (title or "").lower()
    for keywords, folder in KEYWORD_RULES:
        for kw in keywords.split("/"):
            if _boundary_check(t, kw.lower()):
                return folder
    return None
