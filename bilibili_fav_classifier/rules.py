"""Category and tag classification rules.

Bilibili assigns each video an official partition (tname) and user-added tags.
These are more reliable signals than title keywords alone.
"""

# Bilibili official partition (tname) → folder mapping
# Source: https://www.bilibili.com/blackboard/blackroom.html
PARTITION_RULES: dict[str, str] = {
    # 科技区
    "科技": "AI与编程技术",
    "数码": "AI与编程技术",
    "软件应用": "AI与编程技术",
    # 知识区
    "知识": "学习与竞赛",
    "科学科普": "生活与社会",
    "社科·法律·心理": "学习与竞赛",
    "人文历史": "历史与时政",
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
    "动物圈": "生活与社会",
    "汽车": "生活与社会",
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
}

# User-added video tags → folder mapping
# Covers common tags people add to B站 videos
TAG_RULES: list[tuple[str, str]] = [
    # AI & Programming
    ("编程/python/java/c++/代码/算法/claude/cursor/coze/agent/前端/后端/框架/开发/软件/程序员/vscode/git/docker/api/github/linux/debug/开源/人工智能/machine learning/deep learning/神经网络/大模型/llm/rag", "AI与编程技术"),
    # Learning
    ("考研/数学/物理/化学/生物/英语/四级/六级/cet/雅思/托福/论文/科研/sci/竞赛/acm/蓝桥杯/数模/期末/复习/课件/经管/高数/线代/概率/离散/专业课/大学/课程", "学习与竞赛"),
    ("读书/阅读/书籍/书评/文学/哲学", "学习与竞赛"),
    # Gaming & Anime
    ("游戏/gta/原神/三角洲/我的世界/实况/攻略/steam/塞尔达/黑神话/王者/和平精英/lol/csgo/mc/通关/原神/崩坏/星穹铁道/明日方舟/幻塔/鸣潮/抽卡/练度", "游戏与动漫"),
    ("动漫/新番/番剧/鬼灭/咒术/进击的巨人/间谍过家家/鬼畜/名场面/整活/二创/mad/amv", "游戏与动漫"),
    ("Minecraft/我的世界/生存/建筑", "游戏与动漫"),
    # Sports
    ("健身/跑步/减肥/运动/keep/肌肉/拉伸/瑜伽/马拉松/篮球/足球/乒乓/羽毛球/网球/游泳/骑行/街健", "体育"),
    # Music
    ("音乐/翻唱/钢琴/吉他/古筝/日文歌/歌词/歌曲/演唱/mv/bgm/纯音乐/乐理/作曲/编曲/乐队/摇滚/民谣/说唱/rap", "音乐"),
    # Emotion & Copywriting
    ("情感/文案/治愈/感悟/人生/爱情/故事/遗憾/告别/emo/伤感/心理/情商/社交/人际关系", "情感与文案"),
    # History & Politics
    ("历史/二战/苏联/蒋介石/国民党/近代史/朝代/时政/国际/俄乌/特朗普/地缘/资本家/政治/战争/革命/民国", "历史与时政"),
    # Life & Society
    ("美食/做饭/食谱/探店/深夜食堂/厨师/烘焙/家常菜/下厨房", "生活与社会"),
    ("旅行/生活/日常/vlog/大学生/毕业/职场/社畜/租房/独居", "生活与社会"),
    ("科普/知识/冷知识/科学/物理/化学/天文/地理/自然/医学/健康", "生活与社会"),
    ("影视/电影/解说/影评/纪录片/netflix/奥斯卡/豆瓣", "生活与社会"),
    ("汽车/数码/测评/手机/电脑/硬件/iphone/小米/华为/苹果/显卡/笔记本/耳机", "生活与社会"),
    ("搞笑/整活/沙雕/离谱/绷不住/笑点/段子/喜剧", "生活与社会"),
    ("vlog/日常/记录/生活记录", "生活与社会"),
    ("装修/设计/室内/家居", "生活与社会"),
    ("手工/diy/ crafts", "生活与社会"),
    ("摄影/拍照/相机/镜头", "生活与社会"),
    ("三农/农村/种田/养殖", "生活与社会"),
]

# Fallback: title keyword rules (same as before)
KEYWORD_RULES: list[tuple[str, str]] = [
    (
        "编程/开发/技术/AI/代码/算法/Claude/Cursor/Coze/Agent"
        "/Python/Java/C++/前端/后端/框架/引擎/软件/程序"
        "/VSCode/Git/Linux/Docker/API/GitHub/程序员",
        "AI与编程技术",
    ),
    (
        "算法/竞赛/ACM/蓝桥杯/数模/建模/数学/高数/线代/概率"
        "/论文/科研/SCI/英语/四级/六级/CET/雅思/托福"
        "/考研/期末/复习/课件/物理/化学/生物/经管",
        "学习与竞赛",
    ),
    (
        "游戏/GTA/原神/三角洲/我的世界/实况/攻略/Steam"
        "/塞尔达/黑神话/王者/和平精英/实况/LOL/CSGO/MC",
        "游戏与动漫",
    ),
    (
        "动漫/新番/番剧/鬼灭/咒术/进击的巨人/间谍过家家/崩坏",
        "游戏与动漫",
    ),
    ("健身/跑步/减肥/运动/KEEP/肌肉/拉伸/瑜伽", "体育"),
    (
        "音乐/翻唱/钢琴/吉他/古筝/日文歌/歌词/NIGHT DANCER"
        "/歌曲/演唱/MV/BGM/纯音乐",
        "音乐",
    ),
    (
        "情感/文案/治愈/感悟/人生/爱情/故事/遗憾/告别"
        "/EMO/伤感",
        "情感与文案",
    ),
    (
        "历史/二战/苏联/蒋介石/国民党/近代史/朝代"
        "/时政/国际/俄乌/特朗普/访华/地缘政治/资本家",
        "历史与时政",
    ),
    ("美食/做饭/食谱/探店/深夜食堂", "生活与社会"),
    (
        "旅行/生活/日常/Vlog/大学生/毕业/职场/社畜"
        "/科普/知识/冷知识/科学/物理/化学/纪录片"
        "/影视/电影/解说/影评/Netflix/汽车/数码/测评"
        "/手机/电脑/硬件/搞笑/整活/鬼畜/沙雕/离谱",
        "生活与社会",
    ),
]


# ──────────────────────── Matching functions ────────────────────────


def partition_match(tname: str | None) -> str | None:
    if not tname:
        return None
    return PARTITION_RULES.get(tname)


def tag_match(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    # Build a lowercase combined string for matching
    tag_str = " ".join(t.lower() for t in tags)
    for rule_str, folder in TAG_RULES:
        for kw in rule_str.split("/"):
            if kw.lower() in tag_str:
                return folder
    return None


def keyword_classify(title: str) -> str | None:
    t = (title or "").lower()
    for keywords, folder in KEYWORD_RULES:
        for kw in keywords.split("/"):
            if kw.lower() in t:
                return folder
    return None


from bilibili_fav_classifier.mappings import load_seed_mappings


def save_seed_mappings(mappings: dict[str, list[str]]):
    """Save seed mappings via the mappings module."""
    from bilibili_fav_classifier.mappings import save_seed_mappings as _save
    _save(mappings)
