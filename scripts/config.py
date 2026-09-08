#!/usr/bin/env python3
"""경로 해석 — 코퍼스는 형제 저장소(AI Safety)에 있다.

용어집은 자체 저장소지만 원천 데이터(digest.db)와 토픽 분류
(topic_keywords.py)는 동향 Digest 저장소가 갖고 있다. 복제하지 않고
참조한다 — 매일 갱신되는 쪽이 진본이어야 하므로.

  GLOSSARY_DIGEST_REPO 로 위치를 덮어쓸 수 있다.
"""
from __future__ import annotations

import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")

_DEFAULT_DIGEST = os.path.normpath(os.path.join(ROOT, os.pardir, "AI Safety"))
DIGEST_REPO = os.environ.get("GLOSSARY_DIGEST_REPO", _DEFAULT_DIGEST)
DB = os.path.join(DIGEST_REPO, "knowledge", "digest.db")

CANDIDATES = os.path.join(DATA, "glossary_candidates.csv")
TOP100 = os.path.join(DATA, "glossary_top100.csv")
HUBS = os.path.join(DATA, "glossary_top100_hubs.csv")
GLOSS_RANKED = os.path.join(DATA, "glossary_gloss_ranked.csv")
SCORED = os.path.join(DATA, "glossary_candidates_scored.csv")
SITE_JSON = os.path.join(DATA, "glossary.json")


def require_digest_repo() -> None:
    if not os.path.exists(DB):
        sys.exit(
            "동향 코퍼스를 찾을 수 없다: %s\n"
            "  GLOSSARY_DIGEST_REPO=/path/to/'AI Safety' 로 지정하거나,\n"
            "  해당 저장소에서 `python3 mcp_server/build_index.py` 로 digest.db를 만든다."
            % DB
        )


def add_digest_to_path() -> None:
    """topic_keywords.py 를 import 하려면 동향 저장소가 sys.path에 있어야 한다."""
    if DIGEST_REPO not in sys.path:
        sys.path.insert(0, DIGEST_REPO)
