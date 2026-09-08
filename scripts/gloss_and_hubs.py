#!/usr/bin/env python3
"""병기율(정교화) + Top 100 내부 허브 중심성.

centrality.py 에서 배운 것:
  - degree / topic_entropy / PMI-PageRank 는 전부 '일반어 탐지기'였다.
    코퍼스 전체가 이미 AI 안전 문서라서, 그래프 중심성은 개념 위계 대신
    국문 논문·기사의 연결어(문제의식·기여·측면·주로)를 재발견한다.
  - 유일하게 작동한 양의 신호는 병기율이다.

그래서 이 스크립트는 두 가지만 한다.
  1) 병기율 정교화 — 괄호 내용이 실제 뜻풀이인지 검사한다.
     "첨부파일(hwp)"·"모집(~5.30)" 같은 서식 괄호를 걸러낸다.
  2) 허브 중심성 — 확정된 100개 표제어끼리만 그래프를 만든다.
     일반어가 그래프에 없으니 중심성이 제 뜻대로 작동한다.
     선정용이 아니라 '집필 순서·상호참조 설계용' 지표다.
"""
from __future__ import annotations

import csv
import math
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

config.require_digest_repo()
config.add_digest_to_path()

DB = config.DB
TOP = config.TOP100
CAND = config.CANDIDATES
OUT_HUB = config.HUBS
OUT_GLOSS = config.GLOSS_RANKED
OUT_MD = os.path.join(config.ROOT, "glossary_top100.md")
OUT_WATCH = os.path.join(config.ROOT, "glossary_watchlist.md")

# 괄호 내용이 뜻풀이가 아닌 경우
NOT_GLOSS = re.compile(
    r"^\s*(?:"
    r"hwp|pdf|docx?|xlsx?|pptx?|zip|jpe?g|png|gif|hwpx|txt|csv"      # 첨부 서식
    r"|[\d\s.,~\-—:/년월일시분면개건명원%↑↓]+"                          # 숫자·날짜·기간
    r"|[A-Za-z]{1,2}"                                                # 한 두 글자 기호
    r"|주|주식회사|재|사|이하|이상|이하 .{0,10}|현지시간|한국시간"
    r")\s*$", re.I)



def surface_re(term: str) -> "re.Pattern[str]":
    """표기를 원문에서 찾는 정규식.

    후보 추출 때 조사를 떼었으므로 "표현 자유"·"비동 성적" 같은 표기는 원문
    ("표현의 자유", "비동의 성적")에 그대로 없다. 한글 토큰 사이에는 조사가
    붙었을 수 있으니 최대 3자까지 허용한다. 이걸 안 하면 그런 표제어의
    동시출현이 0으로 잡힌다.
    """
    toks = term.split()
    if len(toks) == 1:
        return re.compile(re.escape(term), re.I)
    parts = []
    for i, t in enumerate(toks):
        parts.append(re.escape(t))
        if i < len(toks) - 1:
            parts.append(r"[가-힣]{0,3}\s*" if re.search(r"[가-힣]", t) else r"\s+")
    return re.compile("".join(parts), re.I)

def is_gloss(inner: str) -> bool:
    """괄호 안이 뜻풀이로 보이는가 — 영문 원어 또는 한글 설명구."""
    inner = inner.strip()
    if not inner or len(inner) > 60 or NOT_GLOSS.match(inner):
        return False
    if re.search(r"[A-Za-z]{3,}", inner):
        return True
    return bool(re.search(r"[가-힣]{2,}", inner))


def gloss_counts(rows, terms):
    """term -> (df, 병기_뒤, 병기_안)."""
    pats = {}
    for t in terms:
        base = surface_re(t).pattern
        pats[t] = (
            re.compile(base + r"\s*[(（]([^)）]{0,60})[)）]", re.I),
            re.compile(r"[(（]\s*" + base + r"\s*[)）]", re.I),
            re.compile(base, re.I),
        )
    df, fwd, inside = Counter(), Counter(), Counter()
    for title, summary in rows:
        text = ((title or "") + ". " + (summary or "")).strip()
        if not text:
            continue
        for t, (p_fwd, p_in, p_any) in pats.items():
            if not p_any.search(text):
                continue
            df[t] += 1
            if any(is_gloss(m.group(1)) for m in p_fwd.finditer(text)):
                fwd[t] += 1
            elif p_in.search(text):
                inside[t] += 1
    return df, fwd, inside


def main():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT title, summary FROM items WHERE digest_date IS NOT NULL"
    ).fetchall()
    con.close()

    top = list(csv.DictReader(open(TOP, encoding="utf-8")))
    # 표제어별 코퍼스 표기 집합(대표 + 변이)
    surf = {}
    for r in top:
        vs = [x.split("(")[0].strip()
              for x in r["변이표기"].split(" / ") if x.strip()]
        surf[r["표제어"]] = [v for v in vs if v]

    # --- 1) 허브 중심성: 100개 표제어끼리만 ---
    pats = {h: [surface_re(v) for v in vs] for h, vs in surf.items()}
    heads = list(surf)
    hdf = Counter()
    cooc = defaultdict(Counter)
    ndocs = 0
    for title, summary in rows:
        text = ((title or "") + ". " + (summary or "")).strip()
        if not text:
            continue
        ndocs += 1
        present = [h for h, ps in pats.items() if any(p.search(text) for p in ps)]
        for h in present:
            hdf[h] += 1
        for i, a in enumerate(present):
            for b in present[i + 1:]:
                cooc[a][b] += 1
                cooc[b][a] += 1

    # PMI 가중 + PageRank (노드가 100개뿐이라 일반어 오염이 없다)
    w = defaultdict(dict)
    for a, nb in cooc.items():
        pa = hdf[a] / ndocs
        for b, c in nb.items():
            pb = hdf[b] / ndocs
            pab = c / ndocs
            if min(pa, pb, pab) <= 0:
                continue
            pmi = math.log(pab / (pa * pb))
            if pmi > 0:
                w[a][b] = pmi
    pr = {h: 1.0 / len(heads) for h in heads}
    outw = {a: sum(v.values()) for a, v in w.items()}
    for _ in range(60):
        nxt = {h: 0.15 / len(heads) for h in heads}
        sink = 0.0
        for a in heads:
            tot = outw.get(a, 0.0)
            if tot <= 0:
                sink += pr[a]
                continue
            share = 0.85 * pr[a] / tot
            for b, ww in w[a].items():
                nxt[b] += share * ww
        if sink:
            for h in heads:
                nxt[h] += 0.85 * sink / len(heads)
        s = sum(nxt.values())
        pr = {k: v / s for k, v in nxt.items()}

    gdf, gfwd, gin = gloss_counts(rows, [v for vs in surf.values() for v in vs])

    hub = []
    for r in top:
        h = r["표제어"]
        vs = surf[h]
        tot_df = max((gdf[v] for v in vs), default=0) or 1
        gl = max((gfwd[v] for v in vs), default=0)
        hub.append({
            "bucket": r["bucket"], "표제어": h, "영문": r["영문"],
            "df": r["df"], "recency": r["recency"],
            "이웃표제어수": len(cooc.get(h, ())),
            "허브PR": round(pr[h] * 100, 3),
            "병기문서": gl,
            "병기율": round(gl / tot_df, 3),
        })
    # 괄호 안쪽 등장 = 한글 표제어에 붙는 원어·약어 (반대 방향 신호)
    for r in hub:
        vs = surf[r["표제어"]]
        tot = max((gdf[v] for v in vs), default=0) or 1
        ins = max((gin[v] for v in vs), default=0)
        r["괄호안"] = ins
        r["괄호안율"] = round(ins / tot, 3)

    hub.sort(key=lambda r: -r["허브PR"])
    with open(OUT_HUB, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(hub[0].keys()))
        wr.writeheader()
        wr.writerows(hub)

    # 버킷 순서를 유지한 마크다운
    order = {r["표제어"]: i for i, r in enumerate(top)}
    md = sorted(hub, key=lambda r: order[r["표제어"]])
    prmax = max(r["허브PR"] for r in hub)
    lines = [
        "# AI 안전 용어집 Top 100 표제어", "",
        "코퍼스: `knowledge/digest.db` 5,765건 (2009-04-13 ~ 2026-09-07)", "",
        "| 지표 | 뜻 | 읽는 법 |",
        "|---|---|---|",
        "| `df` | 등장 문서 수 | 원시 빈도가 아니라 문서 수 — 한 사안의 다매체 보도로 부풀지 않음 |",
        "| `m` | 등장한 달 수 | 반짝 용어 배제 |",
        "| `rec` | 최근 12개월 비중 | 1.0에 가까우면 신생 용어 |",
        "| `병기` | 원문이 `표제어(뜻풀이)` 형태로 쓴 문서 수 | 필자가 '설명이 필요하다'고 판단한 흔적 = 용어집 적격성 |",
        "| `괄호안` | 원문이 `한글 표제어(이 표기)` 형태로 쓴 문서 수 | 이 표기가 원어·약어로 붙는다는 뜻 |",
        "| `허브` | 100개 표제어 내부 동시출현 그래프의 PageRank(최대 1.0 정규화) | 높으면 개념망의 중심 — 집필 순서·상호참조 anchor |",
        "",
        "허브 지표는 **선정용이 아니라 집필 설계용**이다. 낮은 값은 '덜 중요하다'가 "
        "아니라 '별개 영역이다'를 뜻한다(피지컬 AI·소버린 AI가 그렇다).",
        "",
        "고유명사(EU AI Act·NIST AI RMF·K-AISI 등)는 표제어에서 제외 — 별도 부록 대상.",
    ]
    cur = None
    for r in md:
        if r["bucket"] != cur:
            cur = r["bucket"]
            i = 0
            lines += ["", "## " + cur, "",
                      "| # | 표제어 | 영문 | df | m | rec | 병기 | 괄호안 | 허브 |",
                      "|---:|---|---|---:|---:|---:|---:|---:|---:|"]
        i += 1
        lines.append("| %d | **%s** | %s | %s | %s | %s | %s | %s | %.2f |" % (
            i, r["표제어"], r["영문"], r["df"], top[order[r["표제어"]]]["months"],
            r["recency"], r["병기문서"], r["괄호안"], r["허브PR"] / prmax))
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    # --- 2) 전체 후보에 대한 병기율 재계산 (누락 표제어 발굴용) ---
    cands = [r for r in csv.DictReader(open(CAND, encoding="utf-8"))
             if int(r["df"]) >= 12]
    terms = [r["term"] for r in cands]
    print("병기율 재계산 대상 %d개" % len(terms), file=sys.stderr)
    d2, f2, i2 = gloss_counts(rows, terms)
    grank = []
    for r in cands:
        t = r["term"]
        dd = d2[t] or int(r["df"])
        grank.append({
            "term": t, "df": int(r["df"]), "months": r["months"],
            "recency": r["recency"], "병기문서": f2[t],
            "병기율": round(f2[t] / dd, 4) if dd else 0.0,
            "괄호안등장": i2[t], "topic1": r["topic1"], "lang": r["lang"],
        })
    grank.sort(key=lambda r: (-r["병기율"], -r["df"]))
    with open(OUT_GLOSS, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(grank[0].keys()))
        wr.writeheader()
        wr.writerows(grank)

    # 관찰 대상: 병기 신호는 있으나 근거가 얇아 Top 100에서 뺀 것들
    inuse = set()
    for r in top:
        for x in r["변이표기"].split(" / "):
            inuse.add(x.split("(")[0].strip().lower())
    watch = [r for r in grank
             if r["term"].lower() not in inuse
             and (r["병기율"] >= 0.15 or r["괄호안등장"] / max(1, r["df"]) >= 0.2)
             and int(r["df"]) >= 12]
    watch.sort(key=lambda r: -(r["병기율"] + r["괄호안등장"] / max(1, r["df"])))
    wl = ["# 관찰 대상 — 다음 갱신에서 재검토", "",
          "병기 신호(원문이 뜻풀이를 붙임)는 뚜렷하지만 Top 100에 넣지 않은 표기.",
          "고유명사·기관명·파이프라인 산출물이 섞여 있으니 사람이 걸러야 한다.", "",
          "| 표기 | df | m | rec | 병기 | 괄호안 | 토픽 |", "|---|---:|---:|---:|---:|---:|---|"]
    for r in watch[:45]:
        wl.append("| %s | %d | %s | %s | %d | %d | %s |" % (
            r["term"], r["df"], r["months"], r["recency"],
            r["병기문서"], r["괄호안등장"], r["topic1"]))
    wl += ["", "## Top 100에서 뺀 것 (근거 부족)", "",
           "- **샌드배깅** (sandbagging, df=6) — 개념적으로는 핵심이나 국문 코퍼스 등장이 6건.",
           "- **모략적 행동** (scheming, df=7) — 같은 이유.",
           "",
           "둘 다 대외 공개용으로는 아직 이르다. 국문 보도가 늘면 되살릴 것."]
    open(OUT_WATCH, "w", encoding="utf-8").write("\n".join(wl) + "\n")

    print("-> %s\n-> %s\n-> %s\n-> %s"
          % (OUT_HUB, OUT_GLOSS, OUT_MD, OUT_WATCH), file=sys.stderr)


if __name__ == "__main__":
    main()
