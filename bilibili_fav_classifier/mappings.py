"""Seed (manual) uploader-to-folder mappings.

This is your personal mapping table — edit it to assign specific UP主 to folders.

Format: { "folder_name": [list of uploader names] }

When you run `autoclassify`, videos from listed uploaders go directly to
the specified folder (highest accuracy).

To add mappings, edit this file or use the save_mappings() function.

All other classification layers (tags → partition → keywords) are defined
in rules.py and work independently of this file.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SEED_FILE = ROOT / "seed_mappings.json"


def load_seed_mappings() -> dict[str, list[str]]:
    if SEED_FILE.exists():
        return json.loads(SEED_FILE.read_text(encoding="utf-8"))
    return {}


def save_seed_mappings(mappings: dict[str, list[str]]):
    SEED_FILE.write_text(
        json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"==> 种子映射已保存到 {SEED_FILE}")
