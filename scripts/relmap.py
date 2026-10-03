#!/usr/bin/env python3
"""용어 관계도 SVG — 카드 안 관계도(ego)와 맨 위 개념 지도.

관계 종류(카드 relations → apply_editorial이 역방향까지 계산해 entry["rel"]에 넣는다)
  up   상위(broader)        down 하위(narrower)       — 포함: 회색 선, 상위 쪽에 빈 삼각형
  pre  전제(requires)                                   — 점선 화살표 (전제 → 이 용어)
  prev 앞 단계(follows_from) next 다음 단계(leads_to)   — 실선 화살표
  vs   대비(contrasts)                                  — 붉은 점선, 양쪽 화살표

라이브러리 없이 문자열로 그린다. 색은 페이지의 CSS 변수를 쓰므로 인라인 SVG로만 넣는다.
"""
from __future__ import annotations

import html

FONT = 13
BOX_H = 28
PAD_X = 11


def text_w(s: str, size: int = FONT) -> float:
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F:
            w += size * 0.98
        elif ch in " ·.()":
            w += size * 0.32
        elif ch.isupper() or ch.isdigit():
            w += size * 0.62
        else:
            w += size * 0.55
    return w


def box_w(label: str) -> float:
    return max(56.0, text_w(label) + 2 * PAD_X)


def clip(cx, cy, w, h, tx, ty):
    """상자 중심 (cx,cy)에서 (tx,ty) 쪽으로 그은 선이 상자 테두리와 만나는 점."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else float("inf")
    sy = (h / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


DEFS = """<defs>
<marker id="{p}-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" style="fill:var(--ink-muted)"/></marker>
<marker id="{p}-arr-vs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" style="fill:var(--accent)"/></marker>
<marker id="{p}-tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto">
<path d="M0,0 L12,6 L0,12 z" style="fill:var(--surface-1);stroke:var(--text-muted);stroke-width:1.4"/></marker>
</defs>"""


def edge_svg(kind, x1, y1, x2, y2, p):
    """(x1,y1)→(x2,y2). broader는 하위→상위 방향으로 넘긴다(삼각형이 상위 쪽)."""
    d = f'M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}'
    if kind == "broader":
        st, mk = "stroke:var(--text-muted);stroke-width:1.4", f'marker-end="url(#{p}-tri)"'
    elif kind == "requires":
        st, mk = "stroke:var(--ink-muted);stroke-width:1.3;stroke-dasharray:5 4", f'marker-end="url(#{p}-arr)"'
    elif kind == "leads_to":
        st, mk = "stroke:var(--ink-muted);stroke-width:1.6", f'marker-end="url(#{p}-arr)"'
    else:  # contrasts
        st, mk = ("stroke:var(--accent);stroke-width:1.3;stroke-dasharray:2 3",
                  f'marker-start="url(#{p}-arr-vs)" marker-end="url(#{p}-arr-vs)"')
    return f'<path class="rel-e rel-{kind}" d="{d}" style="fill:none;{st}" {mk}/>'


def node_svg(n, cx, cy, *, center=False, color="var(--navy)"):
    w = box_w(n["head"])
    x, y = cx - w / 2, cy - BOX_H / 2
    if center:
        rect = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H}" rx="7" '
                f'style="fill:{color};stroke:{color}"/>')
        txt = f'style="fill:#fff;font-weight:700"'
    else:
        rect = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H}" rx="7" '
                f'style="fill:var(--surface-1);stroke:{color};stroke-width:1.3"/>')
        txt = 'style="fill:var(--ink)"'
    label = html.escape(n["head"])
    t = (f'<text x="{cx:.1f}" y="{cy + 4.5:.1f}" text-anchor="middle" font-size="{FONT}" {txt}>{label}</text>')
    inner = rect + t
    if center:
        return f'<g class="rel-n rel-center">{inner}</g>'
    title = f'<title>{html.escape(n["head"] + " · " + n.get("en", ""))}</title>'
    return f'<a class="rel-n" href="#{html.escape(n["id"])}">{title}{inner}</a>'


def _label(x, y, s, anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="11" '
            f'style="fill:var(--text-muted);font-weight:600">{html.escape(s)}</text>')


def ego_svg(e, nodes, color_of, max_side=4):
    """카드 안 관계도. 위=상위, 아래=하위, 왼쪽=전제·앞 단계, 오른쪽=다음 단계·대비."""
    r = e.get("rel") or {}
    get = lambda k, cap=max_side: [nodes[i] for i in (r.get(k) or [])[:cap] if i in nodes]
    up, down = get("up", 3), get("down", 5)
    more_down = len(r.get("down") or []) - len(down)
    left = [("requires", n) for n in get("pre")] + [("leads_to", n) for n in get("prev")]
    right = [("leads_to", n) for n in get("next")] + [("contrasts", n) for n in get("vs")]
    left, right = left[:max_side], right[:max_side]
    if not (up or down or left or right):
        return ""
    p = "e-" + e["id"]
    W = 620
    xl, xc, xr = 100, W / 2, W - 100
    gap = 40
    side_n = max(len(left), len(right), 1)
    top = 26 if up else 0
    yc_band = top + (BOX_H + 30 if up else 26)
    side_h = side_n * gap
    yc = yc_band + max(side_h, gap) / 2
    bottom_y = yc + max(side_h, gap) / 2 + (BOX_H + 10)
    H = (bottom_y + BOX_H / 2 + 10) if down else (yc + max(side_h, gap) / 2 + 6)

    out = [f'<svg class="rel-ego" viewBox="0 0 {W} {H:.0f}" role="img" '
           f'aria-label="{html.escape(e["head"])} 관계도">', DEFS.format(p=p)]
    cw = box_w(e["head"])
    edges, boxes = [], []

    def row(items, y):
        ws = [box_w(n["head"]) for n in items]
        total = sum(ws) + 14 * (len(items) - 1)
        x = xc - total / 2
        pos = []
        for n, w in zip(items, ws):
            pos.append((n, x + w / 2, y))
            x += w + 14
        return pos

    def row_label(items_pos, y, s):
        x0 = min(x - box_w(n["head"]) / 2 for n, x, _ in items_pos)
        out.append(_label(x0 - 10, y + 4, s, "end"))

    if up:
        rp = row(up, top + BOX_H / 2)
        row_label(rp, top + BOX_H / 2, "상위")
        for n, x, y in rp:
            x1, y1 = clip(xc, yc, cw, BOX_H, x, y)
            x2, y2 = clip(x, y, box_w(n["head"]), BOX_H, xc, yc)
            edges.append(edge_svg("broader", x1, y1, x2, y2, p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))
    if down:
        rp = row(down, bottom_y)
        row_label(rp, bottom_y, "하위")
        if more_down > 0:
            x_end = max(x + box_w(n["head"]) / 2 for n, x, _ in rp)
            out.append(_label(x_end + 8, bottom_y + 4, f"+{more_down}", "start"))
        for n, x, y in rp:
            x1, y1 = clip(x, y, box_w(n["head"]), BOX_H, xc, yc)
            x2, y2 = clip(xc, yc, cw, BOX_H, x, y)
            edges.append(edge_svg("broader", x1, y1, x2, y2, p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))

    def column(items, x, side):
        y0 = yc - (len(items) - 1) * gap / 2
        for i, (kind, n) in enumerate(items):
            y = y0 + i * gap
            w = box_w(n["head"])
            if side == "left":
                a = clip(x, y, w, BOX_H, xc, yc)
                b = clip(xc, yc, cw, BOX_H, x, y)
            else:
                a = clip(xc, yc, cw, BOX_H, x, y)
                b = clip(x, y, w, BOX_H, xc, yc)
            edges.append(edge_svg(kind, *a, *b, p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))

    if left:
        column(left, xl, "left")
        kinds = {k for k, _ in left}
        out.append(_label(xl, yc - (len(left) - 1) * gap / 2 - BOX_H / 2 - 7,
                          " · ".join(s for k, s in (("requires", "전제"), ("leads_to", "앞 단계")) if k in kinds)))
    if right:
        column(right, xr, "right")
        kinds = {k for k, _ in right}
        out.append(_label(xr, yc - (len(right) - 1) * gap / 2 - BOX_H / 2 - 7,
                          " · ".join(s for k, s in (("leads_to", "다음 단계"), ("contrasts", "구별")) if k in kinds)))
    out += edges + boxes
    out.append(node_svg(e, xc, yc, center=True, color=color_of(e["id"])))
    out.append("</svg>")
    return "".join(out)


def concept_map_svg(m, nodes, edges, color_of):
    """손으로 배치한 개념 지도. m = {id, w, h, nodes: {id: [x, y]}}; edges = [(a, kind, b)]."""
    p = "m-" + m["id"]
    pos = {k: v for k, v in m["nodes"].items() if k in nodes}
    out = [f'<svg class="rel-map" viewBox="0 0 {m["w"]} {m["h"]}" role="img" '
           f'aria-label="{html.escape(m["title"])}">', DEFS.format(p=p)]
    for a, kind, b in edges:
        if a not in pos or b not in pos:
            continue
        if kind == "requires":  # 전제 → 그 전제가 필요한 용어 (먼저 알 개념에서 화살표가 나간다)
            a, b = b, a
        (ax, ay), (bx, by) = pos[a], pos[b]
        wa, wb = box_w(nodes[a]["head"]), box_w(nodes[b]["head"])
        x1, y1 = clip(ax, ay, wa, BOX_H, bx, by)
        x2, y2 = clip(bx, by, wb, BOX_H, ax, ay)
        out.append(edge_svg(kind, x1, y1, x2, y2, p))
    for k, (x, y) in pos.items():
        out.append(node_svg(nodes[k], x, y, color=color_of(k)))
    for note in m.get("notes") or []:
        out.append(_label(note[0], note[1], note[2], note[3] if len(note) > 3 else "middle"))
    out.append("</svg>")
    return "".join(out)


LEGEND_SVG = """<svg class="rel-legend" viewBox="0 0 560 22" aria-hidden="true">
<defs>
<marker id="lg-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--ink-muted)"/></marker>
<marker id="lg-vs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--accent)"/></marker>
<marker id="lg-tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L12,6 L0,12 z" style="fill:var(--surface-1);stroke:var(--text-muted);stroke-width:1.4"/></marker>
</defs>
<path d="M4,11 L40,11" style="stroke:var(--text-muted);stroke-width:1.4" marker-end="url(#lg-tri)"/><text x="48" y="15" font-size="11.5" style="fill:var(--text-secondary)">하위 → 상위(포함)</text>
<path d="M160,11 L196,11" style="stroke:var(--ink-muted);stroke-width:1.6" marker-end="url(#lg-arr)"/><text x="204" y="15" font-size="11.5" style="fill:var(--text-secondary)">이어짐</text>
<path d="M262,11 L298,11" style="stroke:var(--ink-muted);stroke-width:1.3;stroke-dasharray:5 4" marker-end="url(#lg-arr)"/><text x="306" y="15" font-size="11.5" style="fill:var(--text-secondary)">먼저 알 개념 → 다음</text>
<path d="M424,11 L460,11" style="stroke:var(--accent);stroke-width:1.3;stroke-dasharray:2 3" marker-start="url(#lg-vs)" marker-end="url(#lg-vs)"/><text x="468" y="15" font-size="11.5" style="fill:var(--text-secondary)">혼동 주의</text>
</svg>"""
