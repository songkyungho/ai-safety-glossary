#!/usr/bin/env python3
"""편집 계층을 병합 산출물 위에 얹어 사이트용 JSON을 만든다.

입력
  data/glossary_merged.json   자동 산출 (동향 ∪ PDF) — 손대지 않는다
  data/cards/<id>.json        카드 정본 (표제어·대체어·장·용어 설명·관련 용어·기관별 개념·출처)
  data/chapters.json          구분 ⊃ 장 체계와 장 안 표시 순서
  data/excluded.json          온라인에서 뺀 병합 항목
  data/library_map.json       PDF 근거 문서 → AI 안전 라이브러리 문서 id
  data/doc_titles.json        PDF 근거 문서 제목 표기 바로잡기
  ../ai-safety-research-publish, ../ai-safety-library   관련 연구·정책 문서 (scripts/related.py)
산출
  data/glossary_site.json

카드 하나가 병합 항목 여러 개(join_keys)를 묶을 수 있다. 묶인 항목의 참고 기사와
PDF 원문 인용은 모두 살리고, 지표는 첫 항목(대표) 기준으로 쓴다.
번역어 정본(ai-safety-translation-kit)과 표제어가 어긋나면 경고한다 —
head_override에 사유를 적은 카드는 의도된 차이로 본다.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import related as sibling_links  # noqa: E402

KST = timezone(timedelta(hours=9))
CARDS_DIR = os.path.join(config.DATA, "cards")
CHAPTERS = os.path.join(config.DATA, "chapters.json")
EXCLUDED = os.path.join(config.DATA, "excluded.json")
LIBRARY_MAP = os.path.join(config.DATA, "library_map.json")
DOC_TITLES = os.path.join(config.DATA, "doc_titles.json")
SITE_JSON = os.path.join(config.DATA, "glossary_site.json")
KIT_TERMS = os.environ.get(
    "GLOSSARY_KIT_TERMS",
    os.path.normpath(os.path.join(config.ROOT, os.pardir, "ai-safety-translation-kit", "data", "terms.json")),
)

warnings: list[str] = []


def warn(msg: str) -> None:
    warnings.append(msg)


def nospace(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def strip_paren(s: str) -> str:
    """kit 표기 끝의 약어·주석 괄호를 뗀다: '사고 사슬(CoT)' → '사고 사슬'."""
    return re.sub(r"\s*\(.*\)\s*$", "", s or "")


def load_kit() -> dict:
    if not os.path.exists(KIT_TERMS):
        warn(f"kit 없음 — 번역어 대조를 건너뜀: {KIT_TERMS}")
        return {}
    return {t["id"]: t for t in json.load(open(KIT_TERMS, encoding="utf-8"))["terms"]}


def norm_url(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.rstrip("/")


def digest_dates() -> dict:
    """기사 URL → 다이제스트 게재일. 동향 사이트 날짜 페이지(daily/YYYY-MM-DD.html)로 잇는 데 쓴다."""
    if not os.path.exists(config.DB):
        warn(f"digest.db 없음 — 다이제스트 날짜 링크를 생략: {config.DB}")
        return {}
    con = sqlite3.connect(f"file:{config.DB}?mode=ro", uri=True)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(items)")}
        if not {"url", "digest_date"} <= cols:
            warn("digest.db items 테이블에 url/digest_date가 없음 — 날짜 링크 생략")
            return {}
        # 게시 저장소가 곁에 있으면 실제로 있는 날짜 페이지만 잇는다
        pub = os.path.normpath(os.path.join(config.ROOT, os.pardir, "ai-safety-digest-publish", "daily"))
        pages = {f[:10] for f in os.listdir(pub)} if os.path.isdir(pub) else None
        out = {}
        for url, dd in con.execute("SELECT url, digest_date FROM items WHERE url IS NOT NULL"):
            dd = str(dd or "")[:10]
            if url and dd and (pages is None or dd in pages):
                out.setdefault(norm_url(url), dd)
        return out
    finally:
        con.close()


REL_KINDS = ("broader", "requires", "leads_to", "contrasts")
REL_RANK = {k: i for i, k in enumerate(REL_KINDS)}  # 같은 쌍에 여러 종류면 앞쪽(강한 쪽)을 남긴다


def build_relations(cards: list, ids: set) -> tuple[list, dict]:
    """카드의 relations → 정규화한 간선 목록과 용어별 이웃(역방향 포함).

    간선은 (a, kind, b): broader는 a가 b의 하위, requires는 a가 b를 전제, leads_to는 a 다음 b.
    contrasts는 대칭이라 (작은 id, 큰 id)로 한 번만 둔다.
    """
    best: dict = {}
    for c in cards:
        for kind in REL_KINDS:
            for t in (c.get("relations") or {}).get(kind) or []:
                if t not in ids:
                    warn(f"{c['id']}: relations.{kind}의 id {t} 없음")
                    continue
                if t == c["id"]:
                    continue
                a, b = (c["id"], t)
                if kind == "contrasts":
                    a, b = sorted((a, b))
                pair = tuple(sorted((a, b)))
                old = best.get(pair)
                if old and old[1] != kind:
                    keep = old if REL_RANK[old[1]] <= REL_RANK[kind] else (a, kind, b)
                    warn(f"{pair[0]}–{pair[1]}: 관계 종류가 겹침 ({old[1]}, {kind}) → {keep[1]}만 남김")
                    best[pair] = keep
                elif old and old[1] == kind and (old[0], old[2]) != (a, b) and kind != "contrasts":
                    warn(f"{a}–{b}: {kind}가 양방향으로 적힘 — {old[0]}→{old[2]}만 남김")
                else:
                    best[pair] = (a, kind, b)
    edges = sorted(best.values())
    # broader 순환 점검
    up = {}
    for a, k, b in edges:
        if k == "broader":
            up.setdefault(a, []).append(b)
    def has_cycle(n, seen):
        for m in up.get(n, []):
            if m in seen or has_cycle(m, seen | {m}):
                return True
        return False
    for n in up:
        if has_cycle(n, {n}):
            warn(f"{n}: 상위 관계(broader)에 순환이 있음")
    nb = {i: {k: [] for k in ("up", "down", "pre", "req_by", "prev", "next", "vs")} for i in ids}
    for a, k, b in edges:
        if k == "broader":
            nb[a]["up"].append(b); nb[b]["down"].append(a)
        elif k == "requires":
            nb[a]["pre"].append(b); nb[b]["req_by"].append(a)
        elif k == "leads_to":
            nb[a]["next"].append(b); nb[b]["prev"].append(a)
        else:
            nb[a]["vs"].append(b); nb[b]["vs"].append(a)
    return edges, nb


def main() -> None:
    merged = json.load(open(config.MERGED_JSON, encoding="utf-8"))
    by_jk = {e["join_key"]: e for e in merged["entries"]}
    chap = json.load(open(CHAPTERS, encoding="utf-8"))
    cats = {c["code"]: c for c in chap["categories"]}
    chapters = {c["no"]: c for c in chap["chapters"]}
    excluded = {x["join_key"] for x in json.load(open(EXCLUDED, encoding="utf-8"))}
    libmap = {k: v for k, v in json.load(open(LIBRARY_MAP, encoding="utf-8")).items() if not k.startswith("_")}
    doc_titles = {}
    if os.path.exists(DOC_TITLES):
        doc_titles = {k: v for k, v in json.load(open(DOC_TITLES, encoding="utf-8")).items() if not k.startswith("_")}
    kit = load_kit()
    ddates = digest_dates()

    cards = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(CARDS_DIR, "*.json")))]
    ids = {c["id"] for c in cards}
    heads = {c["id"]: c["head"] for c in cards}

    owner: dict[str, str] = {}
    for c in cards:
        for jk in c.get("join_keys") or []:
            if jk in owner:
                warn(f"{jk}: 카드 {owner[jk]}와 {c['id']}에 중복 배정")
            if jk not in by_jk:
                warn(f"{c['id']}: 병합본에 없는 join_key {jk} (상류 재빌드로 사라졌을 수 있음)")
            owner[jk] = c["id"]
    orphans = sorted(set(by_jk) - set(owner) - excluded)
    for jk in orphans:
        warn(f"카드 없는 병합 항목: {jk} ({by_jk[jk]['head']}) — 표시하지 않음. data/cards에 배정하거나 excluded.json에 넣을 것")

    entries = []
    for c in cards:
        cid = c["id"]
        ch = chapters.get(c.get("chapter"))
        if not ch:
            warn(f"{cid}: 알 수 없는 장 {c.get('chapter')}")
            continue
        cat = cats[ch["category"]]

        # kit 대조
        kid = c.get("kit_id")
        if kid:
            kt = kit.get(kid)
            if kit and not kt:
                warn(f"{cid}: kit에 없는 kit_id {kid}")
            elif kt and nospace(strip_paren(kt["korean"]["preferred"])) != nospace(c["head"]) and not c.get("head_override"):
                warn(f"{cid}: 표제어 '{c['head']}' ≠ kit '{kt['korean']['preferred']}' (head_override 사유 없음)")

        srcs = [by_jk[j] for j in c.get("join_keys") or [] if j in by_jk]
        prim = srcs[0] if srcs else None
        has_d = any(s.get("digest") for s in srcs)
        has_p = any(s.get("pdf") for s in srcs)
        source = "both" if has_d and has_p else "digest" if has_d else "pdf" if has_p else "editor"

        # 참고 기사: 묶인 항목 전체에서 URL 중복 없이, 최신순
        examples, seen = [], set()
        for s in srcs:
            for x in (s.get("digest") or {}).get("examples") or []:
                k = norm_url(x.get("url"))
                if not k or k in seen:
                    continue
                seen.add(k)
                x = dict(x)
                dd = ddates.get(k)
                if dd and not x.get("research"):
                    x["digest_date"] = dd
                examples.append(x)
        examples.sort(key=lambda x: x.get("date") or "", reverse=True)

        # PDF 원문 인용: 문서·쪽 중복 없이
        pdf_defs, seen = [], set()
        for s in srcs:
            for d in (s.get("pdf") or {}).get("definitions") or []:
                k = (d.get("document_id"), d.get("pages_label"), (d.get("quote") or "")[:60])
                if k in seen:
                    continue
                seen.add(k)
                d = dict(d)
                d.update(doc_titles.get(d.get("document_id"), {}))
                lm = libmap.get(d.get("document_id"))
                if lm:
                    d["library_id"] = lm["library_id"]
                pdf_defs.append(d)

        # 출처: 라이브러리 대응이 있으면 붙인다
        refs = []
        for r in c.get("refs") or []:
            r = dict(r)
            ev = r.get("evidence") or {}
            lm = libmap.get(ev.get("document_id"))
            if lm:
                r["library_id"] = lm["library_id"]
            refs.append(r)
        ref_ns = {r.get("n") for r in refs}
        for fw in c.get("frameworks") or []:
            for pt in fw.get("points") or []:
                for n in (pt.get("refs") if isinstance(pt, dict) else None) or []:
                    if n not in ref_ns:
                        warn(f"{cid}: frameworks가 없는 출처 번호 [{n}]를 가리킴")

        # 관련 용어: id → 표제어 링크, {label} → 링크 없는 태그
        related = []
        for r in c.get("related") or []:
            if isinstance(r, str):
                if r in ids and r != cid:
                    related.append({"id": r, "head": heads[r]})
                elif r != cid:
                    warn(f"{cid}: 관련 용어 id {r} 없음")
            elif isinstance(r, dict) and r.get("label"):
                related.append({"label": r["label"]})

        dfn = c.get("definition") or {}
        dig = (prim or {}).get("digest") or {}
        if not dfn.get("lead"):
            # 카드 설명이 아직 없으면 기존 집필 정의로 대신한다
            one = next(((s.get("digest") or {}).get("one") for s in srcs if (s.get("digest") or {}).get("one")), "")
            if one:
                dfn = {"lead": one, "points": []}
            else:
                warn(f"{cid}: 용어 설명 없음")
        commentary = c.get("commentary")
        if commentary is None:
            commentary = next(((s.get("digest") or {}).get("body") for s in srcs if (s.get("digest") or {}).get("body")), []) or []

        variants = []
        for s in srcs:
            d, p = s.get("digest") or {}, s.get("pdf") or {}
            if d.get("variants"):
                variants.append(("동향", str(d["variants"])))
            elif p.get("variants"):
                vv = p["variants"]
                variants.append(("PDF", " · ".join(vv[:8]) if isinstance(vv, list) else str(vv)))

        entries.append({
            "id": cid,
            "head": c["head"],
            "en": c["en"],
            "kit_id": kid,
            "alternatives": [a for a in c.get("alternatives") or [] if a.get("text")],
            "chapter": ch["no"],
            "chapter_label": ch["label"],
            "chapter_en": ch["en"],
            "category": cat["code"],
            "category_label": cat["label"],
            "color": ch.get("color") or cat["color"],
            "category_color": cat["color"],
            "definition": dfn,
            "related": related,
            "frameworks": c.get("frameworks") or [],
            "refs": refs,
            "commentary": commentary,
            "status": c.get("status", "draft"),
            "source": source,
            "join_keys": [s["join_key"] for s in srcs],
            "examples": examples,
            "pdf_definitions": pdf_defs,
            "variants": variants,
            "metrics": {
                "df": (prim or {}).get("df", 0) if has_d else 0,
                "months": dig.get("months", 0),
                "recency": dig.get("recency", 0),
                "gloss": dig.get("gloss", 0),
                "hub_norm": dig.get("hub_norm", 0),
                "pdf_df": max((s.get("pdf_df", 0) for s in srcs), default=0),
                "pdf_gloss_df": max(((s.get("pdf") or {}).get("gloss_df", 0) for s in srcs), default=0),
            },
        })

    rel_stats = sibling_links.attach(entries, warn)   # AI 안전 연구 카탈로그·라이브러리 연결
    rel_edges, rel_nb = build_relations(cards, ids)
    for e in entries:
        e["rel"] = {k: v for k, v in rel_nb.get(e["id"], {}).items() if v}

    # 장 순 → 장 안 지정 순서 → 가나다
    ch_rank = {c["no"]: i for i, c in enumerate(chap["chapters"])}
    pos = {cid: i for c in chap["chapters"] for i, cid in enumerate(c.get("order") or [])}
    entries.sort(key=lambda e: (ch_rank[e["chapter"]], pos.get(e["id"], 10_000), e["head"]))
    for i, e in enumerate(entries, 1):
        e["n"] = i

    n_ch = Counter(e["chapter"] for e in entries)
    n_cat = Counter(e["category"] for e in entries)
    src_counts = Counter(e["source"] for e in entries)
    out = {
        "meta": {
            "title": "AI 안전 용어집",
            "built_at": datetime.now(KST).isoformat(timespec="seconds"),
            "method": "glossary_merged.json + data/cards 편집 계층",
            "counts": {
                "entries": len(entries),
                "cards_with_definition": sum(1 for c in cards if (c.get("definition") or {}).get("lead")),
                "with_frameworks": sum(1 for e in entries if e["frameworks"]),
                "relations": len(rel_edges),
                "linked": rel_stats,
                "merged_used": len(owner),
                "excluded": len(excluded),
                "sources": dict(src_counts),
            },
        },
        "corpus": merged.get("corpus") or {},
        "pdf_meta": merged.get("pdf_meta") or {},
        "categories": [{**c, "n": n_cat.get(c["code"], 0)} for c in chap["categories"]],
        "chapters": [{k: v for k, v in c.items() if k != "order"} | {"n": n_ch.get(c["no"], 0)} for c in chap["chapters"]],
        "relations": [list(x) for x in rel_edges],
        "entries": entries,
    }
    with open(SITE_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    for w in warnings:
        print("  ! " + w)
    print(
        f"site={len(entries)} (카드 설명 {out['meta']['counts']['cards_with_definition']} · "
        f"기관별 {out['meta']['counts']['with_frameworks']}) 병합 사용 {len(owner)} · 제외 {len(excluded)} · "
        f"경고 {len(warnings)} → {SITE_JSON}"
    )


if __name__ == "__main__":
    main()
