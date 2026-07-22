# Bilibili Favorite Folder Classifier

Automatically sort your Bilibili (B站) favorite folder videos into categorized sub-folders using manual uploader mappings and keyword matching.

## How It Works

The classification methodology uses two layers:

1. **Manual mapping** — You pre-assign specific uploaders (UP主) to folders in `up_mappings.json`. This is the most accurate layer.
2. **Keyword matching** — For unmatched uploaders, video titles are scanned against keyword rules to guess the category.

Videos that match neither layer land in "其他" (Others) for manual review.

## Prerequisites

- Python 3.10+
- [Playwright](https://playwright.dev/) (`pip install playwright && playwright install chromium`)

## Setup

1. Clone this repo and install dependencies:

```bash
git clone https://github.com/<your-username>/bilibili-fav-classifier.git
cd bilibili-fav-classifier
pip install playwright requests
playwright install chromium
```

2. Edit `bilibili_fav_classifier/config.py`:
   - Set `USER_MID` to your Bilibili user ID
   - Set `DEFAULT_FAV_ID` to your default favorite folder ID

3. Edit `bilibili_fav_classifier/up_mappings.json`:
   - Map uploader names to folder names
   - Use `python -m bilibili_fav_classifier collect` to generate `up_summary.json` which lists all uploaders in your favorites — use it as reference

## Usage

### Step 1: Collect videos

```bash
python -m bilibili_fav_classifier collect
```

A browser window opens — scan the QR code to log in. The script fetches all videos from your default favorite folder and saves them to `favs.json`.

### Step 2: Auto-classify

```bash
python -m bilibili_fav_classifier autoclassify
```

Generates `plan.json` with the classification plan. Check the output and adjust `up_mappings.json` if needed, then re-run.

For manual-mapping-only classification (no keyword fallback):
```bash
python -m bilibili_fav_classifier genplan
```

### Step 3: Apply

```bash
python -m bilibili_fav_classifier apply
```

Creates the categorized folders (if they don't exist) and moves videos from your default folder. This modifies your Bilibili favorites in place.

To apply only a specific folder:
```bash
python -m bilibili_fav_classifier apply "AI与编程技术"
```

## Output Files

| File | Description |
|------|-------------|
| `cookies.json` | Session cookies (auto-generated, do not commit) |
| `favs.json` | Scraped video list |
| `up_summary.json` | Uploader summary from collect |
| `up_mappings.json` | Your manual uploader → folder mappings |
| `auto_classified.json` | Uploaders matched by keywords (for reference) |
| `plan.json` | Classification plan (review before applying) |
| `apply_log.json` | Results of the apply operation |

## Default Categories

| Folder | Examples |
|--------|----------|
| AI与编程技术 | Programming, AI, Claude, Cursor, code tutorials |
| 学习与竞赛 | Exams, math, physics, English, competitions |
| 游戏与动漫 | Games, anime, Genshin, Valorant, Minecraft |
| 体育 | Fitness, running, basketball, table tennis |
| 音乐 | Music covers, piano, guitar, singing |
| 情感与文案 | Emotional stories, copywriting, life insights |
| 历史与时政 | History, politics, geopolitics |
| 生活与社会 | Daily life, food, travel, tech reviews, comedy |

## Keyword Rules

Defined in `classify.py` → `KEYWORD_RULES`. Edit them to match your viewing patterns.

## License

MIT
