#!/usr/bin/env python3
"""맨 위 전체 개념 지도의 배치를 계산한다 → data/overview_layout.json

용어 전체를 한 장에. 가운데에 'AI 위험'과 'AI 안전'을 두고, 장(data/chapters.json)마다 부채꼴 하나.
  위쪽            01·02 기술과 역량 (양쪽의 바탕)
  오른쪽          08~11 평가·안전 대책, 거버넌스·제도   (AI 안전에서 뻗는다)
  왼쪽            03~07 위험·사고                       (AI 위험에서 뻗는다)
장 대표 용어(HUB)가 가운데와 가깝고, 관계를 따라 바깥 고리로 퍼진다. 고리 하나에 들어갈 개수는
호의 길이로 정하고 넘치면 다음 고리로 보낸다. 가운데와 대표 용어를 잇는 '가지'(spine)는 지도의
뼈대일 뿐 관계 데이터가 아니다.

손으로 고친 좌표를 지키려면 "pinned"에 id를 넣는다(다시 돌려도 움직이지 않는다).
  python3 scripts/layout_overview.py [--reset]   # --reset: pinned를 비우고 새로 계산
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
OUT = os.path.join(config.DATA, "overview_layout.json")

W, H = 1640, 1180
CX, CY = W / 2, H / 2 + 10
CENTER = {"ai-risk": (CX - 95, CY), "ai-safety": (CX + 95, CY)}
SIDE = {"01": "both", "02": "both", "08": "safety", "09": "safety", "10": "safety", "11": "safety",
        "07": "risk", "06": "risk", "05": "risk", "04": "risk", "03": "risk"}
ORDER = ["01", "02", "08", "09", "10", "11", "07", "06", "05", "04", "03"]  # 12시 왼쪽에서 시계 방향
START = -58                       # 01장이 시작하는 각도(12시 기준 시계 방향, 도)
HUB = {"01": "foundation-model", "02": "capability", "03": "risk-management", "04": "misalignment",
       "05": "misuse", "07": "ai-incident", "08": "evaluation", "09": "safeguard", "10": "trustworthy-ai"}
R0 = 150                          # 대표 용어 반지름
KX, KY = 1.3, 0.9                 # 가로로 조금 넓은 타원
GAP_DEG = 2.5                     # 장 사이 여백(도)


def polar(r, deg):
    a = math.radians(deg)
    return CX + r * math.sin(a) * KX, CY - r * math.cos(a) * KY


def arc_len(r, deg_span):
    """타원 고리 위 호 길이의 근사 (가로·세로 반지름 평균)."""
    return r * math.radians(deg_span) * (KX + KY) / 2


def main():
    global W, H, CX, CY
    reset = "--reset" in sys.argv
    site = json.load(open(SITE, encoding="utf-8"))
    ents = {e["id"]: e for e in site["entries"]}
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    pinned = set() if reset else set(old.get("pinned") or [])
    adj = {}
    for a, _, b in site["relations"]:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    members = {ch: sorted(i for i, e in ents.items() if e["chapter"] == ch and i not in CENTER) for ch in ORDER}
    total = sum(len(m) for m in members.values())
    span_all = 360 - GAP_DEG * len(ORDER)
    sectors, a = {}, START
    for ch in ORDER:
        span = span_all * len(members[ch]) / total
        sectors[ch] = (a, a + span)
        a += span + GAP_DEG

    w = {i: relmap.box_w(ents[i]["head"]) for i in ents}
    hh = relmap.BOX_H
    pos, home, hubs = {}, {}, {}
    for c, xy in CENTER.items():
        pos[c] = list(xy)
    ROW_H, GAP_X = hh + 12, 10
    blocks = {}
    for ch in ORDER:
        mem = set(members[ch])
        hub = HUB.get(ch) if HUB.get(ch) in mem else max(sorted(mem), key=lambda v: len(adj.get(v, set()) & mem))
        hubs[ch] = hub
        for v in mem:
            home[v] = ch
        # 관계 순서(BFS)로 줄 세우기 — 이웃끼리 가까이 앉도록
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
        # 블록: 한 줄 최대 폭 안에서 왼쪽→오른쪽으로 채운다
        maxw = 250 if len(order) <= 10 else 330 if len(order) <= 15 else 380
        rows, cur, cw = [], [], 0
        for v in order:
            if cur and cw + w[v] + GAP_X > maxw:
                rows.append(cur); cur, cw = [], 0
            cur.append(v); cw += w[v] + GAP_X
        rows.append(cur)
        bw = max(sum(w[v] + GAP_X for v in r) - GAP_X for r in rows)
        bh = len(rows) * ROW_H
        blocks[ch] = {"rows": rows, "w": bw, "h": bh}

    # 블록 중심을 가운데 둘레에 하나씩 — 겹치지 않는 가장 안쪽 자리 (장 각도는 용어 수에 비례)
    cen, placed = {}, []
    core = (CX - 175, CY - 34, CX + 175, CY + 34)        # 가운데 두 용어 자리
    def hits(x, y, bw, bh):
        r0 = (x - bw / 2 - 16, y - bh / 2 - 14, x + bw / 2 + 16, y + bh / 2 + 14)
        for q in [core] + placed:
            if not (r0[2] < q[0] or r0[0] > q[2] or r0[3] < q[1] or r0[1] > q[3]):
                return True
        return False
    for ch in ORDER:
        a0, a1 = sectors[ch]
        mid = (a0 + a1) / 2
        bw, bh = blocks[ch]["w"], blocks[ch]["h"]
        best = None
        for da in (0, -4, 4, -8, 8, -12, 12):
            r = 90
            while r < 900:
                x, y = polar(r, mid + da)
                if not hits(x, y, bw, bh):
                    break
                r += 4
            if best is None or r < best[3] - 8:
                best = (x, y, mid + da, r)
        x, y, ang, r = best
        cen[ch] = [x, y, ang, r]
        placed.append((x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2))
    for ch in ORDER:
        x, y, mid, _ = cen[ch]
        rows = blocks[ch]["rows"]
        # 대표 용어 줄이 가운데 쪽을 보게: 가운데보다 위에 있는 블록은 줄 순서를 뒤집는다
        if y < CY:
            rows = rows[::-1]
        top = y - blocks[ch]["h"] / 2
        for k, row in enumerate(rows):
            rw = sum(w[v] + GAP_X for v in row) - GAP_X
            xx = x - rw / 2
            for v in row:
                p_ = [xx + w[v] / 2, top + k * ROW_H + ROW_H / 2]
                pos[v] = list(old["nodes"][v]) if v in pinned and v in (old.get("nodes") or {}) else p_
                xx += w[v] + GAP_X

    ids = sorted(home) + list(CENTER)
    xs = [pos[i][0] for i in ids]; ys = [pos[i][1] for i in ids]
    sx0, sy0 = min(xs) - 140, min(ys) - 60
    for i in ids:  # 캔버스 안으로 평행이동
        pos[i][0] -= sx0; pos[i][1] -= sy0
    W = round(max(pos[i][0] for i in ids) + 140)
    H = round(max(pos[i][1] for i in ids) + 60)
    CX, CY = CX - sx0, CY - sy0

    spine = [("ai-risk", "ai-safety")]
    for ch, hub in hubs.items():
        side = SIDE[ch]
        if side in ("risk", "both"):
            spine.append(("ai-risk", hub))
        if side in ("safety", "both"):
            spine.append(("ai-safety", hub))

    chap = {c["no"]: c for c in site["chapters"]}
    boxes = [(pos[i][0] - w[i] / 2 - 4, pos[i][1] - hh / 2 - 4, pos[i][0] + w[i] / 2 + 4, pos[i][1] + hh / 2 + 4)
             for i in ids]
    labels = []   # 장 이름은 섬(블록)의 바깥쪽 가장자리 위에
    for ch in ORDER:
        mem = members[ch]
        x0 = min(pos[i][0] - w[i] / 2 for i in mem); x1 = max(pos[i][0] + w[i] / 2 for i in mem)
        y0 = min(pos[i][1] for i in mem) - hh / 2; y1 = max(pos[i][1] for i in mem) + hh / 2
        cx_ = (x0 + x1) / 2
        outer_top = (y0 + y1) / 2 < CY
        y = y0 - 16 if outer_top else y1 + 16
        labels.append({"theme": ch, "title": f'{ch}. {chap[ch]["label"]}', "x": round(cx_), "y": round(y)})

    out = {
        "_note": "scripts/layout_overview.py 산출(장별 방사형). 손으로 고친 노드는 pinned에 넣으면 다시 계산해도 유지된다.",
        "w": W, "h": H, "center": list(CENTER), "spine": spine, "labels": labels,
        "sectors": {ch: [round(a0, 1), round(a1, 1)] for ch, (a0, a1) in sectors.items()},
        "pinned": sorted(pinned),
        "nodes": {i: [round(pos[i][0]), round(pos[i][1])] for i in ids},
        "home": home,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"nodes={len(ids)} → {OUT}")


if __name__ == "__main__":
    main()
