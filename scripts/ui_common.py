#!/usr/bin/env python3
"""용어집 페이지 크롬 — 틀(머리띠·전역 메뉴·바닥글·CSS)은 ai-safety-common의 chrome이 정본이다.

여기에는 용어집만의 메뉴·태그라인·검색창 문구와 본문 강조 처리만 둔다.
계열색(딥 파인 그린 #2f5951·구리빛 #cf8b5e)은 chrome.PALETTES["glossary"]에 있다.
"""
from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

# 시리즈 사이트 이름·주소·순서는 ai-safety-common/series.json이 정본이다.
sys.path.insert(0, os.environ.get("AI_SAFETY_COMMON") or str(Path.home() / "Code" / "ai-safety-common"))
from aisafety_common import chrome  # noqa: E402

SITE_KEY = "glossary"
NAV_RIGHT = [
    ("about.html", "소개"),
]
TAGLINES = {
    "about.html": "구성과 표제어 원칙, 근거 자료",
}

_EMPHASIS_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_EMPHASIS_UNDER_RE = re.compile(r"__(.+?)__")


def prose_with_emphasis(text: str) -> str:
    """다이제스트와 같이 **굵게** · __밑줄__ 만 살린다. 표제어를 본문에 자동으로 치지 않는다."""
    t = html.escape(text or "")
    t = _EMPHASIS_BOLD_RE.sub(r"<strong>\1</strong>", t)
    t = _EMPHASIS_UNDER_RE.sub(r"<u>\1</u>", t)
    return t.replace("**", "").replace("__", "")


def omnibox_html() -> str:
    return chrome.omnibox_html("표제어 · 대체어 · 영문 · 설명  ( / )")


def page(title: str, current: str, body: str, *, css: str = "", head_count=None, extra_js: str = "") -> str:
    """완성된 HTML 한 장. 첫 화면은 사이트 이름 + 표제어 수, 하위 페이지는 제목 + TAGLINES."""
    if current == "index.html":
        tagline = (f'AI 안전 관점으로 풀어 쓴 핵심 용어 <span id="headCount">{head_count or 0}</span>개.'
                   + chrome.byline_html())
    else:
        tagline = html.escape(TAGLINES.get(current, ""))
    # title_btn="": 하위 페이지의 "← AI 안전 용어집" 단추는 아직 쓰지 않는다 (None으로 바꾸면 알림판·연구처럼 붙는다)
    return chrome.page(SITE_KEY, current, title, body, css=css, js=extra_js, tagline_html=tagline,
                       title_btn="", nav_right=NAV_RIGHT)
