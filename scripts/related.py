#!/usr/bin/env python3
"""용어 ↔ 형제 사이트 연결 — AI 안전 연구 카탈로그의 연구, AI 안전 라이브러리의 정책 문서.

용어마다 표기(한국어 표제어·대체어, 영문, 괄호 속 약어)로 제목·요약을 찾아 몇 건씩 붙인다.
  · 한국어는 띄어쓰기를 무시하고 찾는다. 'AI'를 뗀 표기가 두 글자 이하면 쓰지 않는다('감사'→'감사원' 오탐).
  · 영문은 단어 경계로, 약어(LLM·RLHF 등)는 대소문자까지 맞춘다. 'AI'를 떼면 한 단어만 남는 표기는 쓰지 않는다.
  · 제목에서 맞으면 3점, 요약에서만 맞으면 1점. 연구는 제목 매칭 우선(없으면 요약 2건), 라이브러리는 제목만.
원천
  연구     ../ai-safety-research-publish/index.html 에 실린 데이터(const D = {...})
  라이브러리 ../ai-safety-library/documents.json (in_scope 문서만, 주소는 라이브러리 #doc-id)
형제 저장소가 없으면 빈 결과를 돌려주고 경고만 남긴다.
"""
from __future__ import annotations

import json
import os
import re

import config

RESEARCH_HTML = os.environ.get(
    "GLOSSARY_RESEARCH_HTML",
    os.path.normpath(os.path.join(config.ROOT, os.pardir, "ai-safety-research-publish", "index.html")))
LIBRARY_JSON = os.environ.get(
    "GLOSSARY_LIBRARY_JSON",
    os.path.normpath(os.path.join(config.ROOT, os.pardir, "ai-safety-library", "documents.json")))
PER_TERM = 4
# 한국어 표기가 다른 개념과 겹쳐 오탐이 많은 용어 — 영문으로만 찾는다 ('추론'은 reasoning이기도 하다)
EN_ONLY = {"inference"}


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()


def surface_forms(entry: dict) -> tuple[list[str], list[re.Pattern]]:
    """한국어(띄어쓰기 제거) 표기 목록과 영문 정규식 목록."""
    ko, en = set(), []
    heads = [entry["head"]] + [a["text"] for a in entry.get("alternatives") or []]
    if entry["id"] in EN_ONLY:
        heads = []
    for h in heads:
        if re.search(r"[가-힣]", h):
            k = _nospace(h)
            if len(k) >= 2:
                ko.add(k)
            if h.startswith("AI "):
                k2 = _nospace(h[3:])
                if len(k2) >= 3:
                    ko.add(k2)
    raw = entry["en"]
    base = re.sub(r"\s*\(.*?\)", "", raw).strip()
    abbr = re.findall(r"\(([A-Z][A-Za-z0-9\-]{1,9})\)", raw)
    words = [base]
    if base.lower().startswith("ai ") and len(base.split()) >= 3:
        words.append(base[3:])
    for w_ in words:
        if len(w_) >= 4:
            en.append(re.compile(r"(?<![A-Za-z])" + re.escape(w_).replace(r"\ ", r"[\s\-]") + r"s?(?![A-Za-z])", re.I))
    for a in abbr:
        en.append(re.compile(r"(?<![A-Za-z])" + re.escape(a) + r"s?(?![A-Za-z])"))
    return sorted(ko), en


def _score(ko, en, title: str, summary: str) -> int:
    t_ns, s_ns = _nospace(title), _nospace(summary)
    if any(k in t_ns for k in ko) or any(p.search(title) for p in en):
        return 3
    if any(k in s_ns for k in ko) or any(p.search(summary) for p in en):
        return 1
    return 0


def load_research(warn) -> list[dict]:
    if not os.path.exists(RESEARCH_HTML):
        warn(f"연구 사이트 페이지 없음 — 관련 연구 생략: {RESEARCH_HTML}")
        return []
    s = open(RESEARCH_HTML, encoding="utf-8").read()
    i = s.find("const D = ")
    if i < 0:
        warn("연구 사이트 데이터(const D)를 찾지 못함 — 관련 연구 생략")
        return []
    data, _ = json.JSONDecoder().raw_decode(s[i + len("const D = "):])
    return [{"title": x.get("t") or x.get("o") or "", "orig": x.get("o") or "", "summary": x.get("s") or "",
             "url": x.get("u") or "", "date": x.get("d") or "", "source": x.get("src") or ""}
            for x in data.get("items") or [] if x.get("u")]


def load_library(warn) -> list[dict]:
    if not os.path.exists(LIBRARY_JSON):
        warn(f"라이브러리 문서 목록 없음 — 관련 문서 생략: {LIBRARY_JSON}")
        return []
    docs = json.load(open(LIBRARY_JSON, encoding="utf-8")).get("documents") or []
    out = []
    for d in docs:
        if str(d.get("in_scope")) != "True":
            continue
        title = d.get("title") or d.get("short_name") or ""
        names = " ".join(x for x in (title, d.get("full_name"), d.get("original_name")) if x)
        out.append({"id": d["id"], "title": title, "names": names,
                    "summary": re.sub(r"\*\*", "", d.get("summary") or ""),
                    "date": (d.get("published") or "")[:10], "flag": d.get("flag") or "",
                    "org": d.get("org") or "", "kind": d.get("doc_kind") or ""})
    return out


def attach(entries: list[dict], warn) -> dict:
    """entries에 e["research"], e["library_docs"]를 붙이고 집계를 돌려준다."""
    research, library = load_research(warn), load_library(warn)
    n_r = n_l = 0
    for e in entries:
        ko, en = surface_forms(e)
        seen = {re.sub(r"^https?://(www\.)?", "", (x.get("url") or "").lower()).rstrip("/")
                for x in e.get("examples") or []}
        hits = []
        for x in research:
            sc = _score(ko, en, x["title"] + " " + x["orig"], x["summary"])
            if sc and re.sub(r"^https?://(www\.)?", "", x["url"].lower()).rstrip("/") not in seen:
                hits.append((sc, x["date"], x))
        hits.sort(key=lambda h: (-h[0], h[1] and -int(h[1].replace("-", "")) or 0))
        top = [h for h in hits if h[0] == 3][:PER_TERM] or hits[:2]   # 제목 매칭 우선, 없으면 요약 매칭 2건까지
        e["research"] = [h[2] for h in top]
        hits = []
        for x in library:
            sc = _score(ko, en, x["names"], x["summary"])
            if sc == 3:   # 라이브러리는 제목(문서명)에서 맞은 것만
                hits.append((sc, x["date"], x))
        hits.sort(key=lambda h: (-h[0], h[1] and -int(h[1].replace("-", "")) or 0))
        e["library_docs"] = [{k: v for k, v in h[2].items() if k != "names" and k != "summary"} for h in hits[:PER_TERM]]
        n_r += bool(e["research"]); n_l += bool(e["library_docs"])
    return {"research_pool": len(research), "library_pool": len(library),
            "with_research": n_r, "with_library": n_l}
