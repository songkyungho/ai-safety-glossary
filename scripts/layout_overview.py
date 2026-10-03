#!/usr/bin/env python3
"""맨 위 전체 개념 지도의 배치를 계산한다 → data/overview_layout.json

용어 전체를 한 장에. 장(data/chapters.json)마다 '섬' 하나를 만들고, 섬 맨 위에 그 장의 대표 용어
(HUB, 크게 강조)를 둔 뒤 나머지를 관계 순서대로 줄지어 채운다.
대표 용어 줄이 섬 한가운데에 오고, 관계가 가까운 줄부터 위아래로 번갈아 붙는다.
섬은 4개 열에 위에서 아래로 쌓는다(COLUMNS) — 왼쪽은 위험, 오른쪽은 대책·원칙.

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

# 장 대표 용어 — 섬마다 하나만 크게 강조한다
HUB = {"01": "foundation-model", "02": "capability", "03": "ai-risk", "04": "misalignment",
       "05": "misuse", "06": "disinformation", "07": "ai-incident", "08": "evaluation",
       "09": "safeguard", "10": "ai-safety", "11": "high-risk-ai"}
# 섬을 쌓을 열 — 왼쪽은 위험, 가운데는 기술·사고·평가, 오른쪽은 대책·원칙
COLUMNS = [["04", "03", "05"], ["01", "07", "06"], ["02", "08", "11"], ["09", "10"]]
GAP_ISLAND_X, GAP_ISLAND_Y = 40, 34
LEGEND_H = 150
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

    def make_blocks(maxw_of):
        blocks = {}
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
            maxw = maxw_of(len(order))
            rows, cur, cw = [], [], 0
            for v in order[1:]:
                if cur and cw + w[v] + GAP_X > maxw:
                    rows.append(cur); cur, cw = [], 0
                cur.append(v); cw += w[v] + GAP_X
            if cur:
                rows.append(cur)
            # 대표 용어 줄을 가운데에: 관계가 가까운 줄부터 아래·위로 번갈아 붙인다
            below, above = rows[0::2], rows[1::2]
            layout_rows = [("row", r) for r in above[::-1]] + [("hub", [hub])] + [("row", r) for r in below]
            bw = max([hub_w(ents[hub]["head"])] + [sum(w[v] + GAP_X for v in r) - GAP_X for r in rows])
            bh = sum(HUB_H + 10 if k == "hub" else ROW_H for k, _ in layout_rows)
            blocks[ch] = {"hub": hub, "rows": layout_rows, "w": bw, "h": bh}
        return blocks

    home = {}

    def place(blocks, columns, keep):
        """섬을 열에 쌓고(masonry) 범례를 가장 짧은 열 맨 아래에 둔다 → (좌표, 범례, 폭, 높이)."""
        cen, x, col_box = {}, 0.0, []
        for col in columns:
            cw = max(blocks[ch]["w"] for ch in col)
            y = 0.0
            for ch in col:
                cen[ch] = [x + cw / 2, y + blocks[ch]["h"] / 2]
                y += blocks[ch]["h"] + GAP_ISLAND_Y
            col_box.append((x, cw, y))
            x += cw + GAP_ISLAND_X
        lx, lw, ly = min(col_box, key=lambda c: c[2])
        pos = {}
        for ch in chapters:
            cx_, cy_ = cen[ch]
            B = blocks[ch]
            y = cy_ - B["h"] / 2
            for kind, row in B["rows"]:
                rh = HUB_H + 10 if kind == "hub" else ROW_H
                if kind == "hub":
                    pos[row[0]] = [cx_, y + rh / 2]
                else:
                    rw = sum(w[v] + GAP_X for v in row) - GAP_X
                    xx = cx_ - rw / 2
                    for v in row:
                        pos[v] = [xx + w[v] / 2, y + rh / 2]
                        xx += w[v] + GAP_X
                y += rh
        for v in keep:
            if v in pos:
                pos[v] = list(keep[v])
        hubs_ = {blocks[ch]["hub"] for ch in chapters}
        bw = lambda i: hub_w(ents[i]["head"]) if i in hubs_ else w[i]
        x0 = min([pos[i][0] - bw(i) / 2 for i in pos] + [lx]) - 40
        y0 = min(pos[i][1] for i in pos) - 50
        for i in pos:
            pos[i][0] -= x0; pos[i][1] -= y0
        legend = {"x": round(lx - x0), "y": round(ly - y0), "w": round(lw), "h": LEGEND_H}
        Wc = round(max([pos[i][0] + bw(i) / 2 for i in pos] + [legend["x"] + legend["w"]]) + 40)
        Hc = round(max(max(pos[i][1] for i in pos) + 50, legend["y"] + LEGEND_H + 20))
        return {i: [round(v[0]), round(v[1])] for i, v in pos.items()}, legend, Wc, Hc

    desk_blocks = make_blocks(lambda n: 300 if n <= 10 else 360 if n <= 15 else 400)
    keep = {v: old["nodes"][v] for v in pinned if v in (old.get("nodes") or {})}
    nodes, legend, Wc, Hc = place(desk_blocks, COLUMNS, keep)
    # 모바일: 섬을 한 줄로 세로로 쌓는다 (장 번호 순)
    mob_blocks = make_blocks(lambda n: 330)
    m_nodes, m_legend, mW, mH = place(mob_blocks, [chapters], {})
    hubs = [desk_blocks[ch]["hub"] for ch in chapters]
    out = {
        "_note": "scripts/layout_overview.py 산출(장 섬). 손으로 고친 노드는 pinned에 넣으면 유지된다(넓은 화면 배치만).",
        "w": Wc, "h": Hc, "hubs": hubs, "center": [], "spine": [], "labels": [], "legend": legend,
        "pinned": sorted(pinned), "nodes": nodes, "home": home,
        "mobile": {"w": mW, "h": mH, "legend": m_legend, "nodes": m_nodes},
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"nodes={len(nodes)} canvas={Wc}x{Hc} mobile={mW}x{mH} → {OUT}")


if __name__ == "__main__":
    main()
