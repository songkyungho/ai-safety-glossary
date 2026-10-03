#!/usr/bin/env python3
"""맨 위 전체 개념 지도의 배치를 계산한다 → data/overview_layout.json

용어 전체를 한 장에. 장(data/chapters.json)마다 '섬' 하나를 만들고, 섬 맨 위에 그 장의 대표 용어
(HUB, 크게 강조)를 둔 뒤 나머지를 관계 순서대로 줄지어 채운다.
섬 위치는 장 사이의 실제 관계 수로 정한다 — 연결이 많은 장끼리 서로 당긴다. 큰 흐름을 남기려고
구분별 기준점으로 약하게 당긴다: 기술(01·02)은 위쪽, 위험(03~07)은 왼쪽, 대책·제도(08~11)는 오른쪽.

손으로 고친 좌표를 지키려면 "pinned"에 id를 넣는다(다시 돌려도 움직이지 않는다).
  python3 scripts/layout_overview.py [--reset]   # --reset: pinned를 비우고 새로 계산
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import relmap  # noqa: E402

SITE = os.path.join(config.DATA, "glossary_site.json")
OUT = os.path.join(config.DATA, "overview_layout.json")

# 장 대표 용어 — 섬마다 하나만 크게 강조한다
HUB = {"01": "foundation-model", "02": "capability", "03": "ai-risk", "04": "misalignment",
       "05": "misuse", "06": "disinformation", "07": "ai-incident", "08": "evaluation",
       "09": "safeguard", "10": "ai-safety", "11": "high-risk-ai"}
# 구분별 기준점(가로·세로 비율) — 큰 흐름: 기술 위, 위험 왼쪽, 대책·제도 오른쪽
ANCHOR = {"01": (0.36, 0.12), "02": (0.62, 0.12),
          "03": (0.22, 0.38), "04": (0.08, 0.30), "05": (0.10, 0.70), "06": (0.30, 0.86), "07": (0.40, 0.62),
          "08": (0.64, 0.42), "09": (0.86, 0.30), "10": (0.78, 0.66), "11": (0.58, 0.86)}
W0, H0 = 1700, 900            # 기준점을 놓을 판 크기
ROW_H, GAP_X = relmap.BOX_H + 12, 10
HUB_H = 36


def hub_w(head):
    return relmap.text_w(head, 16) + 36


def main():
    reset = "--reset" in sys.argv
    site = json.load(open(SITE, encoding="utf-8"))
    ents = {e["id"]: e for e in site["entries"]}
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    pinned = set() if reset else set(old.get("pinned") or [])
    adj = {}
    for a, _, b in site["relations"]:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    chapters = [c["no"] for c in site["chapters"]]
    members = {ch: sorted(i for i, e in ents.items() if e["chapter"] == ch) for ch in chapters}
    w = {i: relmap.box_w(ents[i]["head"]) for i in ents}

    # 섬 만들기: 대표 용어는 맨 위 줄에 홀로, 나머지는 관계 순서대로 줄지어
    blocks, home = {}, {}
    for ch in chapters:
        mem = set(members[ch])
        hub = HUB.get(ch) if HUB.get(ch) in mem else max(sorted(mem), key=lambda v: len(adj.get(v, set()) & mem))
        for v in mem:
            home[v] = ch
        order, seen = [], {hub}
        q = deque([hub])
        while True:
            while q:
                u = q.popleft()
                order.append(u)
                for v in sorted(adj.get(u, ()), key=lambda x: -len(adj.get(x, ()))):
                    if v in mem and v not in seen:
                        seen.add(v); q.append(v)
            rest = mem - seen
            if not rest:
                break
            root = max(sorted(rest), key=lambda v: len(adj.get(v, set()) & mem))
            seen.add(root); q.append(root)
        maxw = 320 if len(order) <= 10 else 400 if len(order) <= 15 else 450
        rows, cur, cw = [], [], 0
        for v in order[1:]:
            if cur and cw + w[v] + GAP_X > maxw:
                rows.append(cur); cur, cw = [], 0
            cur.append(v); cw += w[v] + GAP_X
        if cur:
            rows.append(cur)
        bw = max([hub_w(ents[hub]["head"])] + [sum(w[v] + GAP_X for v in r) - GAP_X for r in rows])
        bh = HUB_H + 10 + len(rows) * ROW_H
        blocks[ch] = {"hub": hub, "rows": rows, "w": bw, "h": bh}

    # 섬 위치: 기준점에서 출발해 관계 수만큼 서로 당기고, 겹치면 밀어낸다
    cross = Counter()
    for a, _, b in site["relations"]:
        ca, cb = home[a], home[b]
        if ca != cb:
            cross[tuple(sorted((ca, cb)))] += 1
    cen = {ch: [ANCHOR[ch][0] * W0, ANCHOR[ch][1] * H0] for ch in chapters}
    for it in range(600):
        f = {ch: [0.0, 0.0] for ch in chapters}
        for (a, b), n in cross.items():
            dx, dy = cen[b][0] - cen[a][0], cen[b][1] - cen[a][1]
            d = math.hypot(dx, dy) or 1
            s = 0.0025 * n * d
            f[a][0] += s * dx / d; f[a][1] += s * dy / d
            f[b][0] -= s * dx / d; f[b][1] -= s * dy / d
        for ch in chapters:
            ax, ay = ANCHOR[ch][0] * W0, ANCHOR[ch][1] * H0
            f[ch][0] += 0.03 * (ax - cen[ch][0]); f[ch][1] += 0.03 * (ay - cen[ch][1])
            cen[ch][0] += f[ch][0]; cen[ch][1] += f[ch][1]
        for _ in range(3):
            for i, a in enumerate(chapters):
                for b in chapters[i + 1:]:
                    A, B = cen[a], cen[b]
                    ox = (blocks[a]["w"] + blocks[b]["w"]) / 2 + 40 - abs(A[0] - B[0])
                    oy = (blocks[a]["h"] + blocks[b]["h"]) / 2 + 30 - abs(A[1] - B[1])
                    if ox > 0 and oy > 0:
                        if ox / (blocks[a]["w"] + blocks[b]["w"]) < oy / (blocks[a]["h"] + blocks[b]["h"]):
                            sg = 1 if A[0] <= B[0] else -1
                            A[0] -= sg * ox / 2; B[0] += sg * ox / 2
                        else:
                            sg = 1 if A[1] <= B[1] else -1
                            A[1] -= sg * oy / 2; B[1] += sg * oy / 2

    pos = {}
    for ch in chapters:
        x, y = cen[ch]
        B = blocks[ch]
        top = y - B["h"] / 2
        pos[B["hub"]] = [x, top + HUB_H / 2]
        for k, row in enumerate(B["rows"]):
            rw = sum(w[v] + GAP_X for v in row) - GAP_X
            xx = x - rw / 2
            for v in row:
                pos[v] = [xx + w[v] / 2, top + HUB_H + 10 + k * ROW_H + ROW_H / 2]
                xx += w[v] + GAP_X
    for v in pinned:
        if v in pos and v in (old.get("nodes") or {}):
            pos[v] = list(old["nodes"][v])

    ids = sorted(pos)
    hubs = [blocks[ch]["hub"] for ch in chapters]
    bw = lambda i: hub_w(ents[i]["head"]) if i in hubs else w[i]
    x0 = min(pos[i][0] - bw(i) / 2 for i in ids) - 40
    y0 = min(pos[i][1] for i in ids) - 50
    for i in ids:
        pos[i][0] -= x0; pos[i][1] -= y0
    Wc = round(max(pos[i][0] + bw(i) / 2 for i in ids) + 40)
    Hc = round(max(pos[i][1] for i in ids) + 50)

    out = {
        "_note": "scripts/layout_overview.py 산출(장 섬, 관계 기반 배치). 손으로 고친 노드는 pinned에 넣으면 유지된다.",
        "w": Wc, "h": Hc, "hubs": hubs, "center": [], "spine": [], "labels": [],
        "pinned": sorted(pinned),
        "nodes": {i: [round(pos[i][0]), round(pos[i][1])] for i in ids},
        "home": home,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"nodes={len(ids)} canvas={Wc}x{Hc} → {OUT}")


if __name__ == "__main__":
    main()
