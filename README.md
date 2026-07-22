# Bilibili Favorite Folder Classifier

> 一键把你的 B站「默认收藏夹」整理成分好类的子收藏夹。

你有几百上千条收藏视频堆在一个收藏夹里？这个工具帮你按主题自动分拣——比如「AI 与编程」「学习与竞赛」「游戏与动漫」「音乐」「生活与社会」等等。

---

## 分类逻辑：四层匹配

工具按以下优先级逐层匹配，越往上越准确：

```
视频数据
  │
  ├─ ① 标签匹配    视频的 tag → 文件夹         ← 最精准
  ├─ ② 分区匹配    视频的 tname → 文件夹       ← 官方分类，可靠性高
  ├─ ③ UP主映射    你配置的 UP主 → 文件夹      ← 最可靠，但需要你手动配置
  ├─ ④ 标题关键词  标题里的关键词 → 文件夹     ← 兜底推断
  └─ ⑤ 归入"其他"  没有匹配到 → 等你处理
```

### ① 标签匹配

B站视频自带用户标签（比如你收藏时加「Python」「考研」等标签），以及官方分区标签。工具内置了一套标签→文件夹的规则，匹配成功率最高。

### ② 分区匹配

每个视频有 B站官方分区（`tname`），比如「科技」「游戏」「知识」「生活」等。工具内置了分区→文件夹的映射，覆盖 B站所有主要分区。

### ③ UP主映射

在 `seed_mappings.json` 里配置你常看的 UP主 → 文件夹。这是最可靠的分类方式——你知道自己喜欢看什么。

### ④ 标题关键词

前三层都没命中时，根据视频标题里的关键词做最后推断。

> **核心设计思路**：前三层用结构化的标签和分区数据，尽可能不依赖标题猜，从而把「其他」降到最低。

---

## 完整流程

```
collect ──→ enrich_meta ──→ autoclassify ──→ apply
   │              │                │               │
   │              │                │               └── 创建收藏夹 + 移动视频
   │              │                └── 四层分类 → plan.json
   │              └── 补充视频标签/分区（可选但推荐）
   └── 拉取收藏夹全部视频到本地
```

每次分类前都会先生成 `plan.json`，你检查没问题再跑 `apply`。随时中断，不会丢数据。

---

## 前置要求

- **Python 3.10+**
- **Playwright**（打开浏览器登录 B站）

```bash
pip install playwright requests
playwright install chromium
```

---

## 快速开始

### 1. 克隆并配置

```bash
git clone https://github.com/<你的用户名>/bilibili-fav-classifier.git
cd bilibili-fav-classifier
pip install -r requirements.txt
```

打开 `bilibili_fav_classifier/config.py`，修改两个值：

```python
USER_MID = ""                    # 改成你的 B站用户 ID（纯数字字符串）
DEFAULT_FAV_ID = 0               # 改成你的「默认收藏夹」ID
```

**怎么找 ID？**
- `USER_MID`：打开 `space.bilibili.com`，URL 中 `/` 后面的数字
- `DEFAULT_FAV_ID`：打开收藏夹页面，URL 中 `fid=` 后面的数字

### 2. 配置 UP主映射（可选但推荐）

打开 `bilibili_fav_classifier/seed_mappings.json`：

```json
{
  "AI与编程技术": ["3Blue1Brown", "李永乐老师"],
  "学习与竞赛": ["罗翔说刑法"],
  "游戏与动漫": ["老番茄"]
}
```

> **小技巧**：先跑完 `collect`，会生成 `up_summary.json`，里面列出了你收藏夹里所有 UP主及其视频数量。对照它来填写映射表。

### 3. 运行四步流程

#### Step 1 — 拉取视频

```bash
python -m bilibili_fav_classifier collect
```

浏览器弹出，扫码登录后自动抓取你默认收藏夹里的所有视频，保存到 `favs.json`。

#### Step 2 — 补充标签和分区（推荐）

```bash
python -m bilibili_fav_classifier enrich_meta
```

根据每个视频的 bvid 调用 B站视频详情接口，补充获取**视频标签**和**官方分区**。结果缓存到 `enrich_cache.json`，下次不用重新拉取。

> 这一步是可选的，但强烈推荐——标签和分区数据能大幅减少「其他」的数量。

#### Step 3 — 自动分类

```bash
python -m bilibili_fav_classifier autoclassify
```

脚本按四层优先级分类，输出每个文件夹的视频数量和命中统计：

```
==> 分类命中统计:
    标签匹配:    234
    分区匹配:    89
    UP主映射:    45
    关键词匹配:  32
    归入'其他':  12 个UP主

==> 已生成 plan.json: 8 个文件夹, 共 412 个视频
    - 生活与社会: 120
    - 游戏与动漫: 89
    - AI与编程技术: 67
    - 学习与竞赛: 56
    - 音乐: 32
    - 历史与时政: 28
    - 体育: 20
    - 其他: 12
```

> **检查 `plan.json`**：确认分类结果满意。如果「其他」太多，可以在 `seed_mappings.json` 里补充映射，或者调整 `rules.py` 里的标签/分区/关键词规则，然后重新跑 `autoclassify`。

只用 UP主映射，不做自动推断：

```bash
python -m bilibili_fav_classifier genplan
```

#### Step 4 — 执行分类

```bash
python -m bilibili_fav_classifier apply
```

创建分类收藏夹（已存在就跳过），把视频从「默认收藏夹」批量移动过去。

只跑单个文件夹：

```bash
python -m bilibili_fav_classifier apply "AI与编程技术"
```

---

## 自定义规则

### 修改标签匹配规则

编辑 `bilibili_fav_classifier/rules.py` → `TAG_RULES`：

```python
TAG_RULES = [
    ("编程/python/java/...", "AI与编程技术"),
    ("考研/数学/...", "学习与竞赛"),
    # 添加你自己的规则
    ("你的标签/关键词", "文件夹名"),
]
```

### 修改分区匹配规则

编辑 `bilibili_fav_classifier/rules.py` → `PARTITION_RULES`：

```python
PARTITION_RULES = {
    "科技": "AI与编程技术",
    "游戏": "游戏与动漫",
    # 添加你自己的规则
}
```

### 查看 B站有哪些分区

B站的分区列表见：[B站分区-blackboard](https://www.bilibili.com/blackboard/blackroom.html)

---

## 默认分类文件夹

| 文件夹 | 对应标签/分区关键词 |
|--------|-------------------|
| **AI与编程技术** | 标签含「编程/代码/AI/Claude/Cursor」，分区=科技/软件应用 |
| **学习与竞赛** | 标签含「考研/数学/英语/竞赛/论文」，分区=知识/社科 |
| **游戏与动漫** | 标签含「游戏/原神/MC/攻略」，分区=游戏 |
| **体育** | 标签含「健身/跑步/乒乓」，分区=运动 |
| **音乐** | 标签含「翻唱/钢琴/吉他」，分区=音乐 |
| **情感与文案** | 标签含「情感/治愈/文案」 |
| **历史与时政** | 标签含「历史/时政/二战」 |
| **生活与社会** | 标签含「美食/Vlog/数码/搞笑」，分区=生活/娱乐/影视 |

---

## 生成的文件

| 文件 | 说明 | 提交到 Git？ |
|------|------|:----------:|
| `cookies.json` | 登录凭证 | 不要 |
| `favs.json` | 抓取的视频列表 | 不要 |
| `enrich_cache.json` | 标签/分区缓存 | 不要 |
| `seed_mappings.json` | **你的 UP主 → 文件夹 映射表** | 建议提交（你自己的配置） |
| `up_summary.json` | UP主统计（填映射表时参考） | 不要 |
| `auto_classified.json` | 关键词匹配到的未手动映射的 UP主 | 不要 |
| `plan.json` | 分类计划（apply 前检查） | 不要 |
| `apply_log.json` | apply 执行结果 | 不要 |

---

## 常见问题

**Q: enrich_meta 太慢怎么办？**

工具有文件缓存 (`enrich_cache.json`)，第二次运行会跳过已缓存的视频。首次运行时每 0.5 秒请求一个，1000 个视频大约 8-10 分钟。之后 `autoclassify` 不需要重新 enrich。

**Q: 不想跑 enrich_meta 可以吗？**

可以。直接跑 `autoclassify`，没有标签/分区数据时会跳过这两层，只用 UP映射 + 关键词匹配。但「其他」的数量会多一些。

**Q: 分类错了怎么改？**

先在 B站收藏夹页面手动调整，然后：
- 如果是某个 UP主的视频总被分错 → 加到 `seed_mappings.json`
- 如果是某类标签总被分错 → 改 `rules.py` 里的 `TAG_RULES`
- 如果是某类分区被分错 → 改 `PARTITION_RULES`

**Q: 会删除我原来的视频吗？**

不会。`apply` 只是把视频从「默认收藏夹」**移动**到分类收藏夹，视频不会被删除或取消收藏。

**Q: 会封号吗？**

每次 API 请求之间有延迟，频率远低于正常用户操作。B站 WAF 偶尔会限流，脚本会自动等待 60 秒重试。合理使用没问题。

**Q: 我想分享我的 seed_mappings.json？**

可以提交到自己的 repo。但注意 `seed_mappings.json` 包含你常看的 UP主名字，属于个人偏好数据。

---

## License

MIT — 随便用，随便改。
