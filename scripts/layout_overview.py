#!/usr/bin/env python3
"""맨 위 전체 개념 지도의 배치를 계산한다 → data/overview_layout.json

하나의 큰 지도. 가운데에 'AI 위험'과 'AI 안전'을 두고, 주제마다 부채꼴 하나를 준다.
  위쪽            기술과 역량 (양쪽의 바탕)
  왼쪽 반원       위험이 생기는 곳 — 모델 행동 · 오용 · 사고   (AI 위험에서 뻗는다)
  오른쪽 반원     어떻게 다루나   — 위험 관리 · 평가 · 신뢰할 수 있는 AI (AI 안전에서 뻗는다)
주제의 대표 용어(HUB)가 가운데와 가깝고, 관계를 한 단계 건널 때마다 바깥 고리로 나간다.
가운데와 대표 용어를 잇는 '가지'(SPINE)는 지도의 뼈대일 뿐 관계 데이터가 아니다.

여러 주제에 걸친 용어는 PRIORITY 순서로 한 주제에만 둔다.
손으로 고친 좌표를 지키려면 "pinned"에 id를 넣는다.
  python3 scripts/layout_overview.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import relmap  # noqa: E402

SITE = os.path.join(config.DATA, "glossary_site.json")
THEMES = os.path.join(config.DATA, "concept_maps.json")
OUT = os.path.join(config.DATA, "overview_layout.json")

W, H = 1400, 940
CX, CY = W / 2, H / 2
CENTER = {"ai-risk": (CX - 90, CY), "ai-safety": (CX + 90, CY)}
# 주제: (대표 용어, 시작 각, 끝 각) — 각도는 12시 방향에서 시계 방향(도)
SECTORS = {
    "tech":         ("capability",       -46,  46),
    "risk-process": ("risk-management",   48,  92),
    "evaluation":   ("evaluation",        94, 136),
    "trustworthy":  ("trustworthy-ai",   138, 182),
    "incidents":    ("ai-incident",      184, 228),
    "misuse":       ("misuse",           230, 270),
    "behaviour":    ("misalignment",     272, 312),
}
SPINE = [  # (가운데 쪽, 대표 용어)
    ("ai-risk", "ai-safety"),
    ("ai-risk", "capability"), ("ai-safety", "capability"),
    ("ai-risk", "misalignment"), ("ai-risk", "misuse"), ("ai-risk", "ai-incident"),
    ("ai-safety", "risk-management"), ("ai-safety", "evaluation"), ("ai-safety", "trustworthy-ai"),
]
PRIORITY = ["incidents", "behaviour", "misuse", "evaluation", "risk-process", "trustworthy", "tech"]
R0, DR = 130, 92          # 대표 용어 반지름, 고리 간격(최대)
KX, KY = 1.45, 0.84       # 가로로 넓은 타원


def edge_radius(deg, margin=30):
    """그 방향으로 캔버스 가장자리까지 갈 수 있는 반지름(타원 좌표)."""
    a = math.radians(deg)
    sx, sy = math.sin(a) * KX, -math.cos(a) * KY
    rs = []
    if sx > 1e-6: rs.append((W - margin - 60 - CX) / sx)
    if sx < -1e-6: rs.append((CX - margin - 60) / -sx)
    if sy > 1e-6: rs.append((H - margin - CY) / sy)
    if sy < -1e-6: rs.append((CY - margin) / -sy)
    return min(rs)


def polar(r, deg):
    a = math.radians(deg)
    return CX + r * math.sin(a) * KX, CY - r * math.cos(a) * KY


def main():
    site = json.load(open(SITE, encoding="utf-8"))
    themes = {t["id"]: t for t in json.load(open(THEMES, encoding="utf-8"))["themes"]}
    ents = {e["id"]: e for e in site["entries"]}
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    pinned = set(old.get("pinned") or [])

    home = {}
    for tid in PRIORITY:
        for i in themes[tid]["terms"]:
            if i in ents and i not in home and i not in CENTER:
                home[i] = tid
    for tid, (hub, _, _) in SECTORS.items():
        home[hub] = tid
    ids = sorted(home) + list(CENTER)
    adj = {}
    for a, _, b in site["relations"]:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    pos, init = {}, {}
    for c, xy in CENTER.items():
        pos[c] = list(xy)
    for tid, (hub, a0, a1) in SECTORS.items():
        mem = {i for i, t in home.items() if t == tid}
        depth, parent = {hub: 0}, {hub: None}
        q = deque([hub])
        while q:
            u = q.popleft()
            for v in sorted(adj.get(u, ())):
                if v in mem and v not in depth:
                    depth[v] = depth[u] + 1
                    parent[v] = u
                    q.append(v)
        while mem - set(depth):  # 대표 용어와 끊긴 묶음은 연결이 가장 많은 용어를 1단계에 두고 펼친다
            rest = mem - set(depth)
            root = max(sorted(rest), key=lambda v: len(adj.get(v, set()) & mem))
            depth[root], parent[root] = 1, hub
            q = deque([root])
            while q:
                u = q.popleft()
                for v in sorted(adj.get(u, ())):
                    if v in rest and v not in depth:
                        depth[v] = depth[u] + 1
                        parent[v] = u
                        q.append(v)
        maxd = max(depth.values()) or 1
        rb = min(edge_radius(a0 + (a1 - a0) * f) for f in (0.15, 0.5, 0.85))
        dr = max(46, min(DR, (rb - R0) / maxd))   # 공간이 좁은 갈래(위·아래)는 고리를 촘촘히
        ang = {hub: (a0 + a1) / 2}
        for d in range(1, max(depth.values()) + 1):
            ring = [v for v in mem if depth[v] == d]
            ring.sort(key=lambda v: (ang.get(parent[v], (a0 + a1) / 2), v))
            n = len(ring)
            for k, v in enumerate(ring):
                ang[v] = a0 + (a1 - a0) * (k + 0.5) / n
        for v in mem:
            r = R0 + depth[v] * dr + (14 if depth[v] and len([u for u in mem if depth[u] == depth[v]]) > 4 and
                                         sorted(u for u in mem if depth[u] == depth[v]).index(v) % 2 else 0)
            init[v] = polar(r, ang[v])
            pos[v] = list(old["nodes"][v]) if v in pinned and v in (old.get("nodes") or {}) else list(init[v])

    w = {i: relmap.box_w(ents[i]["head"]) for i in ids}
    hh = relmap.BOX_H

    def clamp(i):
        pos[i][0] = min(max(pos[i][0], w[i] / 2 + 8), W - w[i] / 2 - 8)
        pos[i][1] = min(max(pos[i][1], hh / 2 + 8), H - hh / 2 - 8)

    for it in range(300):
        for i in ids:  # 처음 자리로 약하게 당긴다 — 부채꼴 모양 유지 (마지막 80회는 겹침만 푼다)
            if i in CENTER or i in pinned or it >= 220:
                continue
            pos[i][0] += 0.04 * (init[i][0] - pos[i][0])
            pos[i][1] += 0.04 * (init[i][1] - pos[i][1])
        for x in range(len(ids)):
            i = ids[x]
            for y in range(x + 1, len(ids)):
                j = ids[y]
                ox = (w[i] + w[j]) / 2 + 12 - abs(pos[i][0] - pos[j][0])
                oy = hh + 12 - abs(pos[i][1] - pos[j][1])
                if ox > 0 and oy > 0:
                    fi = 0 if (i in CENTER or i in pinned) else 1
                    fj = 0 if (j in CENTER or j in pinned) else 1
                    if fi + fj == 0:
                        continue
                    if ox < oy:
                        sgn = 1 if pos[i][0] <= pos[j][0] else -1
                        mv = (ox + 0.5) / (fi + fj)
                        pos[i][0] -= sgn * mv * fi; pos[j][0] += sgn * mv * fj
                    else:
                        sgn = 1 if pos[i][1] <= pos[j][1] else -1
                        mv = (oy + 0.5) / (fi + fj)
                        pos[i][1] -= sgn * mv * fi; pos[j][1] += sgn * mv * fj
        for i in ids:
            clamp(i)

    labels = []   # 주제 이름은 갈래의 가장 바깥 용어 바로 바깥에. 용어와 겹치면 안쪽으로 비켜 간다
    boxes = [(pos[i][0] - w[i] / 2 - 4, pos[i][1] - hh / 2 - 4, pos[i][0] + w[i] / 2 + 4, pos[i][1] + hh / 2 + 4)
             for i in ids]
    for tid, (hub, a0, a1) in SECTORS.items():
        mid = (a0 + a1) / 2
        mem = [i for i, t in home.items() if t == tid]
        rmax = max(math.hypot((pos[i][0] - CX) / KX, (pos[i][1] - CY) / KY) for i in mem)
        lw = relmap.text_w(themes[tid]["title"], 12) + 20
        def free(x, y):
            return not any(not (x + lw / 2 < b0 or x - lw / 2 > b2 or y + 11 < b1 or y - 11 > b3)
                           for b0, b1, b2, b3 in boxes)
        best = None
        for da in (0, -6, 6, -12, 12, -18, 18):        # 바깥으로만 비켜 가고, 막히면 각도를 바꾼다
            ang = mid + da
            r = rmax + 30
            while r < edge_radius(ang, margin=-60):
                x, y = polar(r, ang)
                x = min(max(x, lw / 2 + 6), W - lw / 2 - 6)
                y = min(max(y, 14), H - 14)
                if free(x, y):
                    best = (x, y)
                    break
                r += 6
            if best:
                break
        x, y = best or polar(rmax + 30, mid)
        labels.append({"theme": tid, "title": themes[tid]["title"], "x": round(x), "y": round(y)})

    out = {
        "_note": "scripts/layout_overview.py 산출(방사형). 손으로 고친 노드는 pinned에 넣으면 다시 계산해도 유지된다.",
        "w": W, "h": H, "center": list(CENTER), "spine": SPINE, "labels": labels,
        "pinned": sorted(pinned),
        "nodes": {i: [round(pos[i][0]), round(pos[i][1])] for i in ids},
        "home": home,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"nodes={len(ids)} → {OUT}")


if __name__ == "__main__":
    main()
