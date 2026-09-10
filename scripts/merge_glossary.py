#!/usr/bin/env python3
"""동향 Glossary + PDF Glossary 를 en-norm 으로 조인해 병합 JSON을 만든다.

산출: data/glossary_merged.json
  - source: digest | pdf | both
  - 버킷은 동향판을 우선. PDF-only 는 매핑표로 동향 버킷에 붙인다.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import pdf_config as pcfg  # noqa: E402

KST = timezone(timedelta(hours=9))

# config.MERGED_JSON
MERGED_JSON = config.MERGED_JSON
# PDF 버킷 코드 → 동향 버킷 코드
PDF_BUCKET_MAP = {
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "E": "E",
    "F": "F",
    "G": "G",
    "H": "I",  # 정보생태계·합성미디어
    "I": "L",  # 기반 기술
    "J": "Z",  # 기타·횡단 (동향에 없던 잔여)
}

Z_BUCKET = {
    "code": "Z",
    "label": "기타·횡단",
    "color": "#57534e",
}


def norm_key(en: str, head: str = "") -> str:
    s = (en or head or "").lower().replace("\u00ad", "")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9가-힣]+", "", s)
    return s


def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def map_pdf_bucket(code: str) -> str:
    return PDF_BUCKET_MAP.get(code, "Z")


def digest_slim(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": e["n"],
        "head": e["head"],
        "en": e["en"],
        "alt": e.get("alt"),
        "one": e.get("one") or "",
        "body": e.get("body") or [],
        "src": e.get("src"),
        "examples": e.get("examples") or [],
        "df": e.get("df", 0),
        "months": e.get("months", 0),
        "recency": e.get("recency", 0),
        "gloss": e.get("gloss", 0),
        "paren": e.get("paren", 0),
        "hub": e.get("hub", 0),
        "hub_norm": e.get("hub_norm", 0),
        "variants": e.get("variants") or "",
        "surface": e.get("surface"),
        "neighbors": e.get("neighbors") or [],
    }


def pdf_slim(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": e["n"],
        "head": e["head"],
        "en": e["en"],
        "definitions": e.get("definitions") or [],
        "df": e.get("df", 0),
        "gloss_df": e.get("gloss_df", 0),
        "chunk_hits": e.get("chunk_hits", 0),
        "year_span": e.get("year_span", 0),
        "score": e.get("score", 0),
        "status": e.get("status", "found"),
        "n_defs": e.get("n_defs", len(e.get("definitions") or [])),
        "variants": e.get("variants") or [],
        "bucket_code_orig": e.get("bucket_code"),
    }


def main() -> None:
    if not os.path.exists(config.SITE_JSON):
        sys.exit(f"동향 JSON 없음: {config.SITE_JSON}")
    if not os.path.exists(pcfg.SITE_JSON):
        sys.exit(f"PDF JSON 없음: {pcfg.SITE_JSON} — 먼저 ./run_pdf_build.sh")

    digest = load_json(config.SITE_JSON)
    pdf = load_json(pcfg.SITE_JSON)

    d_by: dict[str, dict] = {}
    for e in digest["entries"]:
        k = norm_key(e.get("en") or "", e.get("head") or "")
        if k:
            d_by[k] = e

    p_by: dict[str, dict] = {}
    for e in pdf["entries"]:
        k = norm_key(e.get("en") or "", e.get("head") or "")
        if k:
            p_by[k] = e

    bucket_meta = {b["code"]: b for b in digest["buckets"]}
    bucket_meta["Z"] = Z_BUCKET

    keys = sorted(set(d_by) | set(p_by))
    entries: list[dict[str, Any]] = []

    for k in keys:
        d = d_by.get(k)
        p = p_by.get(k)
        if d and p:
            source = "both"
            head = d["head"]
            en = d["en"] or p["en"]
            alt = d.get("alt")
            bc = d["bucket_code"]
            label = d["bucket"]
            color = d["color"]
        elif d:
            source = "digest"
            head = d["head"]
            en = d["en"]
            alt = d.get("alt")
            bc = d["bucket_code"]
            label = d["bucket"]
            color = d["color"]
        else:
            assert p is not None
            source = "pdf"
            head = p["head"]
            en = p["en"]
            alt = None
            bc = map_pdf_bucket(p["bucket_code"])
            bm = bucket_meta[bc]
            label = bm["label"]
            color = bm["color"]

        entry: dict[str, Any] = {
            "join_key": k,
            "source": source,
            "head": head,
            "en": en,
            "alt": alt,
            "bucket_code": bc,
            "bucket": label,
            "color": color,
            "digest": digest_slim(d) if d else None,
            "pdf": pdf_slim(p) if p else None,
        }
        # 카드·정렬용 평탄 지표
        if d:
            entry["df"] = d.get("df", 0)
            entry["months"] = d.get("months", 0)
            entry["recency"] = d.get("recency", 0)
            entry["gloss"] = d.get("gloss", 0)
            entry["hub_norm"] = d.get("hub_norm", 0)
            entry["one"] = d.get("one") or ""
        else:
            entry["df"] = p.get("df", 0) if p else 0
            entry["months"] = 0
            entry["recency"] = 0
            entry["gloss"] = p.get("gloss_df", 0) if p else 0
            entry["hub_norm"] = 0
            entry["one"] = ""
        if p:
            entry["pdf_df"] = p.get("df", 0)
            entry["pdf_score"] = p.get("score", 0)
        else:
            entry["pdf_df"] = 0
            entry["pdf_score"] = 0
        entries.append(entry)

    # 버킷·점수 순 정렬 후 번호
    order = {b["code"]: i for i, b in enumerate(digest["buckets"])}
    order["Z"] = len(order)
    entries.sort(
        key=lambda e: (
            order.get(e["bucket_code"], 99),
            0 if e["source"] == "both" else 1 if e["source"] == "digest" else 2,
            -e.get("df", 0),
            e["head"],
        )
    )
    for i, e in enumerate(entries, 1):
        e["n"] = i

    # 버킷 집계 (동향 버킷 + Z)
    buckets = []
    for b in digest["buckets"]:
        buckets.append(
            {
                "code": b["code"],
                "label": b["label"],
                "color": b["color"],
                "n": sum(1 for e in entries if e["bucket_code"] == b["code"]),
            }
        )
    z_n = sum(1 for e in entries if e["bucket_code"] == "Z")
    if z_n:
        buckets.append({**Z_BUCKET, "n": z_n})

    src_counts = Counter(e["source"] for e in entries)
    out = {
        "meta": {
            "title": "AI 안전 용어집",
            "built_at": datetime.now(KST).isoformat(timespec="seconds"),
            "method": "digest ∪ pdf join on normalized English",
            "sources": {
                "digest": len(digest["entries"]),
                "pdf": len(pdf["entries"]),
                "merged": len(entries),
                "both": src_counts.get("both", 0),
                "digest_only": src_counts.get("digest", 0),
                "pdf_only": src_counts.get("pdf", 0),
            },
        },
        "corpus": digest.get("corpus") or {},
        "pdf_meta": {
            "coverage": (pdf.get("meta") or {}).get("coverage"),
            "method": (pdf.get("meta") or {}).get("method"),
        },
        "buckets": buckets,
        "entries": entries,
    }

    os.makedirs(config.DATA, exist_ok=True)
    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        f"merged={len(entries)} both={src_counts.get('both', 0)} "
        f"digest_only={src_counts.get('digest', 0)} "
        f"pdf_only={src_counts.get('pdf', 0)} → {MERGED_JSON}"
    )


if __name__ == "__main__":
    main()
