#!/usr/bin/env python3
"""후보 용어에 중심성·병기율 지표를 붙인다.

왜 중심성만으로는 안 되나: 원시 동시출현 중심성은 "기술·정부·기업"처럼
아무 데나 붙는 일반어를 최상위로 올린다. 그래서 두 갈래로 나눠 본다.

  degree         동시출현하는 서로 다른 용어 수 → 높을수록 일반어 의심
  pagerank_pmi   PMI 가중 그래프 PageRank → 특이성 보정된 중심성
  topic_entropy  17개 토픽에 걸친 분산(정규화) → 영역 관통하는 기초 개념
  gloss_rate     원문이 괄호로 원어/설명을 붙인 문서 비율
                 → "정렬(alignment)"처럼 필자가 직접 '설명이 필요하다'고
                   판단한 흔적. 용어집 적격성의 가장 직접적인 증거.

입력: glossary_candidates.csv (extract_candidates.py 산출)
출력: glossary_candidates_scored.csv
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

import extract_candidates as ex  # noqa: E402
from topic_keywords import TOPIC_KEYWORDS, match_topics  # noqa: E402

DB = config.DB
SRC = config.CANDIDATES
OUT = config.SCORED

VOCAB_N = 2500      # 그래프에 올릴 상위 후보 수
PR_ITER = 40
DAMPING = 0.85


def main():
    cands = list(csv.DictReader(open(SRC, encoding="utf-8")))
    cands.sort(key=lambda r: -float(r["score"]))
    vocab = {r["term"].lower(): r for r in cands[:VOCAB_N]}
    print("vocab=%d (전체 후보 %d)" % (len(vocab), len(cands)), file=sys.stderr)

    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT title, summary FROM items WHERE digest_date IS NOT NULL"
    ).fetchall()
    con.close()

    df = Counter()
    cooc = defaultdict(Counter)
    topic_dist = defaultdict(Counter)
    gloss = Counter()
    ndocs = 0

    for n, (title, summary) in enumerate(rows, 1):
        text = ((title or "") + ". " + (summary or "")).strip()
        if not text:
            continue
        ndocs += 1
        terms = set()
        for t in ex.ko_terms(text) + ex.en_terms(text):
            k = t.lower()
            if k in vocab:
                terms.add(k)
        doc_topics = match_topics(text, TOPIC_KEYWORDS)
        lowtext = text.lower()
        for k in terms:
            df[k] += 1
            for tp in doc_topics:
                topic_dist[k][tp] += 1
            # 병기: "용어(...)" 또는 "(용어)" — 필자가 원어/설명을 덧붙인 자리
            if re.search(re.escape(k) + r"\s*[(（]", lowtext) or \
               re.search(r"[(（]\s*" + re.escape(k) + r"\s*[)）]", lowtext):
                gloss[k] += 1
        ts = sorted(terms)
        for i, a in enumerate(ts):
            for b in ts[i + 1:]:
                cooc[a][b] += 1
                cooc[b][a] += 1
        if n % 1000 == 0:
            print("  %d/%d" % (n, len(rows)), file=sys.stderr)

    # PMI 가중 그래프. 음수 PMI(=우연보다 덜 붙는 쌍)는 버린다.
    weights = defaultdict(dict)
    for a, nbrs in cooc.items():
        pa = df[a] / ndocs
        for b, c in nbrs.items():
            pb = df[b] / ndocs
            pab = c / ndocs
            if pab <= 0 or pa <= 0 or pb <= 0:
                continue
            pmi = math.log(pab / (pa * pb))
            if pmi > 0:
                weights[a][b] = pmi

    nodes = list(vocab)
    pr = {k: 1.0 / len(nodes) for k in nodes}
    outw = {a: sum(w.values()) for a, w in weights.items()}
    for _ in range(PR_ITER):
        nxt = {k: (1 - DAMPING) / len(nodes) for k in nodes}
        sink = 0.0
        for a in nodes:
            tot = outw.get(a, 0.0)
            if tot <= 0:
                sink += pr[a]
                continue
            share = DAMPING * pr[a] / tot
            for b, w in weights[a].items():
                nxt[b] += share * w
        if sink:
            add = DAMPING * sink / len(nodes)
            for k in nodes:
                nxt[k] += add
        s = sum(nxt.values())
        pr = {k: v / s for k, v in nxt.items()}

    ntopic = len(TOPIC_KEYWORDS)
    out = []
    for k, r in vocab.items():
        d = df[k] or int(r["df"])
        deg = len(cooc.get(k, ()))
        dist = topic_dist[k]
        tot = sum(dist.values())
        if tot:
            ent = -sum((c / tot) * math.log(c / tot) for c in dist.values())
            ent /= math.log(ntopic)
        else:
            ent = 0.0
        out.append({
            "term": r["term"],
            "df": int(r["df"]),
            "months": int(r["months"]),
            "recency": float(r["recency"]),
            "score_freq": float(r["score"]),
            "degree": deg,
            "degree_norm": round(deg / max(1, len(nodes) - 1), 4),
            "pagerank_pmi": round(pr[k] * 1e4, 4),
            "topic_entropy": round(ent, 4),
            "gloss_rate": round(gloss[k] / d, 4) if d else 0.0,
            "gloss_docs": gloss[k],
            "topic1": r["topic1"],
            "words": int(r["words"]),
            "lang": r["lang"],
        })

    out.sort(key=lambda r: -r["pagerank_pmi"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print("-> " + OUT, file=sys.stderr)


if __name__ == "__main__":
    main()
