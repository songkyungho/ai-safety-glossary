#!/usr/bin/env python3
"""표제어 + 지표 + 실제 용례를 data/glossary.json 으로 조립한다.

용례는 코퍼스에서 직접 뽑는다. 고르는 순서:
  1) 구체적인 변이 표기로 걸린 문서를 먼저 (변이 목록은 구체어 우선이므로
     `지평`·`감사` 같은 광의 표기로 걸린 것보다 `시간 지평`이 앞선다)
  2) 원문이 그 표제어를 병기한 문서(= 필자가 뜻을 풀어 준 자리)
  3) 그다음 최근 문서
placeholder 요약(`요약불가` 등)은 제외한다 — 용례로 쓸 수 없다.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

config.require_digest_repo()
config.add_digest_to_path()

from definitions import DEFS  # noqa: E402
from gloss_and_hubs import is_gloss, surface_re  # noqa: E402

N_EXAMPLES = 3
POOL_PER_HEAD = 40  # 정렬 전에 모아 두는 후보 수
PLACEHOLDER = ("요약불가", "요약 불가", "확인 필요", "본문 내용 없음",
               "제공된 정보", "내용 없음", "정보 없음")

BUCKET_META = {
    "A": ("정렬·모델 행동", "#3d3a6e"),
    "B": ("안전성 평가·측정", "#1d4ed8"),
    "C": ("오용·악용 위험", "#be123c"),
    "D": ("에이전트·자율성", "#0369a1"),
    "E": ("거버넌스·책임 원칙", "#3f5340"),
    "F": ("법·규제 개념", "#7c3aed"),
    "G": ("표준·인증·위험관리", "#0f766e"),
    "H": ("보안·사이버 위협", "#b45309"),
    "I": ("정보생태계·합성미디어", "#a21caf"),
    "J": ("국가안보·중대위험", "#9f1239"),
    "K": ("이용자 보호", "#c2410c"),
    "L": ("기반 기술·모델 공개", "#475569"),
    "M": ("AI 주권·물리 AI", "#166534"),
}


def variants_of(row):
    out = []
    for chunk in row["변이표기"].split(" / "):
        v = chunk.split("(")[0].strip()
        if v:
            out.append(v)
    return out


def main():
    top = list(csv.DictReader(open(config.TOP100, encoding="utf-8")))
    hubs = {r["표제어"]: r for r in csv.DictReader(open(config.HUBS, encoding="utf-8"))}

    con = sqlite3.connect(config.DB)
    rows = con.execute(
        "SELECT title, summary, url, source, digest_date, article_date, is_research "
        "FROM items WHERE digest_date IS NOT NULL ORDER BY digest_date DESC"
    ).fetchall()
    con.close()

    pats = {}
    for r in top:
        vs = variants_of(r)
        pats[r["표제어"]] = [
            (i, surface_re(v),
             re.compile(surface_re(v).pattern + r"\s*[(（]([^)）]{0,60})[)）]", re.I))
            for i, v in enumerate(vs)
        ]

    picked = defaultdict(list)
    for title, summary, url, source, ddate, adate, is_res in rows:
        text = ((title or "") + ". " + (summary or "")).strip()
        if not text or any(p in text for p in PLACEHOLDER):
            continue
        for head, ps in pats.items():
            if len(picked[head]) >= POOL_PER_HEAD:
                continue
            vidx = None
            glossed = False
            for i, p_any, p_gloss in ps:
                if p_any.search(text):
                    vidx = i
                    glossed = any(is_gloss(m.group(1))
                                  for m in p_gloss.finditer(text))
                    break
            if vidx is not None:
                picked[head].append({
                    "_vidx": vidx,
                    "title": title or "(제목 없음)",
                    "url": url or "",
                    "source": source or "",
                    "date": adate or ddate or "",
                    "research": bool(is_res),
                    "_glossed": glossed,
                })

    entries = []
    for i, r in enumerate(top):
        head = r["표제어"]
        code = r["bucket"].split(".")[0].strip()
        label, color = BUCKET_META.get(code, (r["bucket"], "#475569"))
        h = hubs.get(head, {})
        cands = picked.get(head, [])
        # 안정 정렬 3단: 날짜 내림차순 → 병기 우선 → 구체 변이 우선
        cands.sort(key=lambda x: x["date"], reverse=True)
        cands.sort(key=lambda x: 0 if x["_glossed"] else 1)
        cands.sort(key=lambda x: x["_vidx"])
        ex = []
        seen = set()
        for c in cands:
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            ex.append({k: v for k, v in c.items()
                       if not k.startswith("_")})
            if len(ex) >= N_EXAMPLES:
                break
        d = DEFS.get(head) or {}
        entries.append({
            "n": i + 1,
            "head": head,
            "en": r["영문"],
            "alt": d.get("alt") or "",
            "one": d.get("one", ""),
            "body": list(d.get("body", ())),
            "src": d.get("src", ""),
            "bucket_code": code,
            "bucket": label,
            "color": color,
            "surface": r["대표표기"],
            "variants": r["변이표기"],
            "df": int(r["df"]),
            "months": int(r["months"]),
            "recency": float(r["recency"]),
            "gloss": int(h.get("병기문서", 0) or 0),
            "paren": int(h.get("괄호안", 0) or 0),
            "hub": float(h.get("허브PR", 0) or 0),
            "neighbors": int(h.get("이웃표제어수", 0) or 0),
            "examples": ex,
        })

    prmax = max((e["hub"] for e in entries), default=1) or 1
    for e in entries:
        e["hub_norm"] = round(e["hub"] / prmax, 3)

    buckets = []
    for code, (label, color) in BUCKET_META.items():
        n = sum(1 for e in entries if e["bucket_code"] == code)
        if n:
            buckets.append({"code": code, "label": label, "color": color, "n": n})

    con = sqlite3.connect(config.DB)
    # digest_date 가 빈 문자열인 행이 있어 MIN 이 ''로 나온다 — 걸러낸다.
    total, dmin, dmax = con.execute(
        "SELECT COUNT(*), MIN(digest_date), MAX(digest_date) FROM items "
        "WHERE digest_date IS NOT NULL AND digest_date != ''"
    ).fetchone()
    con.close()

    payload = {
        "entries": entries,
        "buckets": buckets,
        "corpus": {"docs": total, "from": dmin, "to": dmax},
        "no_example": [e["head"] for e in entries if not e["examples"]],
        "no_def": [e["head"] for e in entries if not e["one"]],
    }
    with open(config.SITE_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("표제어 %d개 · 정의 %d개 · 용례 없는 항목 %d개 · 코퍼스 %d건"
          % (len(entries), len(entries) - len(payload["no_def"]),
             len(payload["no_example"]), total))
    unknown = sorted(set(DEFS) - {e["head"] for e in entries})
    if unknown:
        print("  !! 표제어에 없는 정의 키(오타?): " + ", ".join(unknown))
    if payload["no_def"]:
        print("  정의 미작성 %d개: %s"
              % (len(payload["no_def"]), ", ".join(payload["no_def"])))
    if payload["no_example"]:
        print("  용례 없음: " + ", ".join(payload["no_example"]))
    print("-> " + config.SITE_JSON)


if __name__ == "__main__":
    main()
