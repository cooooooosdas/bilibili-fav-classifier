"""CLI entry point for bilibili-fav-classifier.

Pipeline: collect → enrich_meta → autoclassify → apply
"""
from __future__ import annotations

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bilibili_fav_classifier.classify_core import autoclassify, genplan
from bilibili_fav_classifier.collect import collect as _collect
from bilibili_fav_classifier.enrich import enrich_meta
from bilibili_fav_classifier.session import Session


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "collect":
        asyncio.run(_collect())
    elif cmd == "enrich_meta":
        enrich_meta()
    elif cmd == "autoclassify":
        autoclassify()
    elif cmd == "genplan":
        genplan()
    elif cmd == "apply":
        session = Session.load()
        csrf = session.csrf
        from bilibili_fav_classifier.apply import apply as _apply
        _apply(session.http(), csrf, sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
