# Bilibili Favorite Folder Classifier

> 一键把你的 B站「默认收藏夹」整理成分好类的子收藏夹。

你有几百上千条收藏视频堆在一个收藏夹里？这个工具帮你按主题自动分拣——比如「AI 与编程」「学习与竞赛」「游戏与动漫」「音乐」「生活与社会」等等。

---

## 它怎么工作？

整个流程分三层，越往上越准确：

```
你的收藏视频
    │
    ├── 第一层：手动映射  ──→ 你指定的 UP主 → 固定文件夹（最准）
    │
    ├── 第二层：关键词匹配 ──→ 视频标题含有关键词 → 推断文件夹（不错）
    │
    └── 第三层：归入"其他" ──→ 没匹配上的 → 等你手动处理
```

- **手动映射**：你在 `up_mappings.json` 里写 "某个 UP主 → 某个文件夹"。这是最可靠的分类方式，因为你知道自己喜欢看什么。
- **关键词匹配**：没手动映射的 UP主，脚本会看他发的视频标题里有没有关键词。比如标题带「Python」归到「AI与编程技术」，带「考研」归到「学习与竞赛」。
- **兜底**：两层都没命中的，先放进「其他」，你可以之后再手动调整。

---

## 完整流程（三步走）

```
collect ──→ autoclassify ──→ apply
   │             │               │
   │             │               └── 创建收藏夹 + 移动视频（真正改你的B站数据）
   │             └── 生成分类计划（先检查，再 apply）
   └── 拉取收藏夹里的全部视频到本地
```

> **重要**：每次分类前都会先生成 `plan.json`，你检查没问题再跑 `apply`。可以随时中断，不会丢数据。

---

## 前置要求

- **Python 3.10 或更高版本**
- **Playwright**（用于打开浏览器登录 B站）

```bash
# 安装依赖
pip install playwright requests

# 安装 Chromium 浏览器（只需一次）
playwright install chromium
```

---

## 快速开始

### 第一步：克隆并配置

```bash
git clone https://github.com/<你的用户名>/bilibili-fav-classifier.git
cd bilibili-fav-classifier
pip install -r requirements.txt  # 如果存在的话，没有就装上面那两个包
```

然后打开 `bilibili_fav_classifier/config.py`，修改两个值：

```python
USER_MID = "350016742"           # ← 改成你的 B站用户 ID
DEFAULT_FAV_ID = 197359242       # ← 改成你的「默认收藏夹」ID
```

**怎么找自己的 ID？**

1. 打开 https://space.bilibili.com ，登录后点右上角头像 → 「个人中心」
2. URL 里 `space.bilibili.com/` 后面的数字就是你的 `USER_MID`
3. 打开你的收藏夹页面，URL 类似 `space.bilibili.com/12345/favlist?fid=9876543`，`fid=` 后面的数字就是 `DEFAULT_FAV_ID`

### 第二步：映射 UP主到文件夹

打开 `bilibili_fav_classifier/up_mappings.json`，格式如下：

```json
{
  "学习与竞赛": ["李永乐老师", "3Blue1Brown", "罗翔说刑法"],
  "音乐": ["张学友", "周杰伦"],
  "游戏与动漫": ["老番茄", "某幻君"]
}
```

意思是：李永乐老师的视频 → 放进「学习与竞赛」文件夹，以此类推。

> **小技巧**：先运行 `collect`（见下一步），会生成 `up_summary.json`，里面列出了你收藏夹里所有 UP主及其视频数量。对照它来填写映射表，不会漏。

### 第三步：运行三步流程

#### Step 1 — 拉取视频

```bash
python -m bilibili_fav_classifier collect
```

会弹出一个浏览器窗口，用 B站 APP 扫码登录。登录成功后，脚本会自动抓取你默认收藏夹里的所有视频信息（标题、UP主、BV号），保存到 `favs.json`。

完成后控制台会显示类似这样的信息：

```
==> 共拉取 523 条视频
==> 已保存到 favs.json
==> 下一步: 运行 autoclassify 自动分类, 再运行 apply
```

#### Step 2 — 自动分类

```bash
python -m bilibili_fav_classifier autoclassify
```

脚本会：
1. 用 `up_mappings.json` 里的手动映射分类
2. 对没映射到的视频，按标题关键词自动推断
3. 生成 `plan.json`（分类计划）

控制台会输出每个文件夹的视频数量：

```
==> 已生成 plan.json: 10 个文件夹, 共 523 个视频
    - 情感与文案: 87
    - 生活与社会: 120
    - AI与编程技术: 45
    - 学习与竞赛: 68
    - 游戏与动漫: 102
    - 其他: 42
==> 归入'其他'的UP主: ['某个UP主名', ...]
```

> **检查 `plan.json`**：确认分类结果满意。如果有不满意的，去改 `up_mappings.json` 或关键词规则，然后重新跑 `autoclassify`。

#### Step 3 — 执行分类（移动视频）

```bash
python -m bilibili_fav_classifier apply
```

这一步会真正操作你的 B站账号：
1. 在 B站上创建 `plan.json` 里的各个收藏夹（已存在就跳过）
2. 把视频从「默认收藏夹」批量移动到对应分类收藏夹

控制台会实时显示进度：

```
==> 创建收藏夹: AI与编程技术
    创建成功 id=4077695842

==> AI与编程技术: 批次 1: 50/50 (累计 50/50)
==> AI与编程技术: 移动 45/45 成功 (失败0)
```

只跑单个文件夹（比如只想先分好「AI与编程」）：

```bash
python -m bilibili_fav_classifier apply "AI与编程技术"
```

---

## 自定义分类文件夹

默认分类有 8 个文件夹：

| 文件夹 | 包含内容 |
|--------|----------|
| **AI与编程技术** | 编程、AI、Claude、Cursor、Python、代码教程 |
| **学习与竞赛** | 考研、数学、物理、英语、论文、竞赛 |
| **游戏与动漫** | 游戏攻略、新番动漫、Minecraft、黑神话 |
| **体育** | 健身、跑步、乒乓球、羽毛球 |
| **音乐** | 翻唱、钢琴、吉他、古筝、日文歌 |
| **情感与文案** | 情感故事、治愈文案、人生感悟 |
| **历史与时政** | 历史讲解、国际时政、地缘政治 |
| **生活与社会** | 美食、旅行、Vlog、数码测评、搞笑整活 |

**想改文件夹名或数量？** 直接改 `up_mappings.json` 里的 key 就行。`autoclassify` 会自动按你定义的文件夹名生成计划。

**想改关键词规则？** 编辑 `bilibili_fav_classifier/classify.py` 里的 `KEYWORD_RULES` 列表。

---

## 生成的文件说明

运行过程中会产生以下文件：

| 文件 | 说明 | 需要提交到 Git？ |
|------|------|:-:|
| `cookies.json` | 登录凭证（自动生成） | 不要 |
| `favs.json` | 抓取的视频列表 | 不要 |
| `up_summary.json` | UP主统计（填写映射表时参考用） | 不要 |
| `up_mappings.json` | **你的 UP主 → 文件夹 映射表** | 建议提交 |
| `auto_classified.json` | 关键词匹配到的未手动映射的 UP主 | 不要 |
| `plan.json` | 分类计划（apply 前人工检查） | 不要 |
| `apply_log.json` | apply 执行结果日志 | 不要 |

> `cookies.json` 等包含个人信息的文件已加入 `.gitignore`，不会被意外提交。

---

## 常见问题

**Q: 不想用关键词匹配，只想用手动映射怎么办？**

用 `genplan` 代替 `autoclassify`：

```bash
python -m bilibili_fav_classifier genplan
```

这个命令只用 `up_mappings.json` 里的手动映射，不做关键词推断。没映射到的全部归入「其他」。

**Q: 收藏夹有 1000 条上限，视频太多放不下怎么办？**

B站每个收藏夹最多 1000 条视频。如果某个分类文件夹的视频超过 1000 条，可以在 `up_mappings.json` 里再细分（比如「游戏与动漫」拆成「游戏与动漫」「游戏与动漫2」），或者在 `apply` 时手动分批。

**Q: 分类错了怎么改？**

在 B站收藏夹页面手动调整即可。然后更新 `up_mappings.json`，下次重新运行 `autoclassify` + `apply` 时会修正。

**Q: 会删除我原来的视频吗？**

不会。`apply` 只是把视频从「默认收藏夹」**移动**到分类收藏夹，视频本身不会被删除或取消收藏。你的其他收藏夹不受影响。

**Q: 会不会被封号？**

脚本在每次 API 请求之间有 1.5 秒延迟，批量移动时也有冷却时间，频率远低于正常用户操作。但如果几百条视频一次性跑，B站 WAF（防火墙）偶尔会限流——脚本会自动等待 60 秒重试。合理使用没问题。

**Q: 我想贡献代码 / 提问题**

欢迎开 Issue 或 PR！[GitHub Issues](https://github.com/cooooooosdas/bilibili-fav-classifier/issues)

---

## License

MIT — 随便用，随便改。
