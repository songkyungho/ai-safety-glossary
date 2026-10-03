#!/usr/bin/env python3
"""용어 관계도 SVG — 맨 위 전체 개념 지도와 카드 안 관계도.

시각 언어 (두 그림이 같다)
  노드    구분 색을 옅게 채운 알약. 연결이 많은 핵심 용어는 조금 굵게.
  이어짐  (leads_to)  진한 곡선 화살표
  먼저 알 개념 (requires) 옅은 곡선 화살표 — 전제 → 그 전제가 필요한 용어
  포함    (broader)   전체 지도에서는 상위어와 하위어를 옅은 영역으로 묶고, 선은 가늘게만
  혼동 주의 (contrasts) 아주 옅은 선 + 가운데 '≠' 배지

entry["rel"]의 이웃 키: up(상위) down(하위) pre(먼저 알 개념) prev(앞 단계) next(다음 단계) vs(혼동 주의).
라이브러리 없이 문자열로 그린다. 색은 페이지 CSS 변수를 쓰므로 인라인 SVG로만 넣는다.
"""
from __future__ import annotations

import html
import math

FONT = 12.5
BOX_H = 26
PAD_X = 12


def text_w(s: str, size: float = FONT) -> float:
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
    return max(48.0, text_w(label) + 2 * PAD_X)


def clip(cx, cy, w, h, tx, ty):
    """알약 중심에서 (tx,ty) 쪽으로 그은 선이 테두리와 만나는 점(사각형 근사)."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else float("inf")
    sy = (h / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def defs(p):
    return f"""<defs>
<marker id="{p}-a1" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--ink-muted)"/></marker>
<marker id="{p}-a2" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--text-muted);opacity:.75"/></marker>
</defs>"""


def curve(x1, y1, x2, y2, bend=0.14):
    """살짝 휜 2차 베지어. 굽는 방향은 좌표 순서로 정해져 같은 쌍은 늘 같은 쪽으로 휜다."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    k = bend * min(L, 260)
    cx, cy = mx - dy / L * k, my + dx / L * k
    return f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}", (mx * 0.5 + cx * 0.5, my * 0.5 + cy * 0.5)


def edge_svg(kind, x1, y1, x2, y2, p, a="", b=""):
    attrs = f'class="rel-e k-{kind}" data-a="{a}" data-b="{b}"'
    if kind == "contrasts":
        d, _ = curve(x1, y1, x2, y2, 0.0)
        mx, my = x1 + (x2 - x1) * 0.62, y1 + (y2 - y1) * 0.62  # 배지는 대상 쪽으로 — 한 점에서 뻗을 때 겹치지 않게
        return (f'<g {attrs}><path d="{d}" style="fill:none;stroke:var(--accent);stroke-width:1;stroke-opacity:.45;stroke-dasharray:1 3"/>'
                f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="7.5" style="fill:var(--surface-1);stroke:var(--accent);stroke-width:1"/>'
                f'<text x="{mx:.1f}" y="{my + 3.6:.1f}" text-anchor="middle" font-size="10.5" '
                f'style="fill:var(--accent);font-weight:700">≠</text></g>')
    if kind == "broader":
        d, _ = curve(x1, y1, x2, y2, 0.0)
        return f'<path {attrs} d="{d}" style="fill:none;stroke:var(--text-muted);stroke-width:1;stroke-opacity:.45"/>'
    d, _ = curve(x1, y1, x2, y2)
    if kind == "leads_to":
        st, mk = "stroke:var(--ink-muted);stroke-width:1.5;stroke-opacity:.8", f"url(#{p}-a1)"
    else:  # requires
        st, mk = "stroke:var(--text-muted);stroke-width:1.2;stroke-opacity:.6", f"url(#{p}-a2)"
    return f'<path {attrs} d="{d}" style="fill:none;{st}" marker-end="{mk}"/>'


def node_svg(n, cx, cy, *, center=False, color="var(--navy)", hub=False):
    w = box_w(n["head"])
    x, y = cx - w / 2, cy - BOX_H / 2
    r = BOX_H / 2
    if center:
        rect = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H}" rx="{r}" style="fill:{color}"/>'
        txt = 'style="fill:#fff;font-weight:700"'
    else:
        rect = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H}" rx="{r}" '
                f'style="fill:color-mix(in srgb, {color} 13%, var(--surface-1));'
                f'stroke:color-mix(in srgb, {color} 38%, transparent);stroke-width:1"/>')
        txt = f'style="fill:var(--ink);font-weight:{650 if hub else 500}"'
    t = (f'<text x="{cx:.1f}" y="{cy + 4.3:.1f}" text-anchor="middle" font-size="{FONT}" {txt}>'
         f'{html.escape(n["head"])}</text>')
    if center:
        return f'<g class="rel-n rel-center">{rect}{t}</g>'
    title = f'<title>{html.escape(n["head"] + " · " + n.get("en", ""))}</title>'
    return (f'<a class="rel-n" data-id="{html.escape(n["id"])}" href="#{html.escape(n["id"])}">'
            f'{title}{rect}{t}</a>')


def _label(x, y, s, anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="10.5" '
            f'style="fill:var(--text-muted);font-weight:600;letter-spacing:.02em">{html.escape(s)}</text>')


def _link(kind, a_xy, a_w, b_xy, b_w, p, a="", b=""):
    x1, y1 = clip(a_xy[0], a_xy[1], a_w, BOX_H, *b_xy)
    x2, y2 = clip(b_xy[0], b_xy[1], b_w, BOX_H, *a_xy)
    if kind in ("leads_to", "requires"):  # 화살촉이 알약에 붙지 않게 조금 띄운다
        L = math.hypot(x2 - x1, y2 - y1) or 1
        x2 -= (x2 - x1) / L * 2.5
        y2 -= (y2 - y1) / L * 2.5
    return edge_svg(kind, x1, y1, x2, y2, p, a, b)


# ── 카드 안 관계도 ────────────────────────────────────────────────

def ego_svg(e, nodes, color_of, max_side=4):
    """위=상위, 아래=하위, 왼쪽=먼저 알 개념·앞 단계, 오른쪽=다음 단계·혼동 주의."""
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
    xl, xc, xr = 104, W / 2, W - 104
    gap = 38
    side_n = max(len(left), len(right), 1)
    top = 22 if up else 0
    yc_band = top + (BOX_H + 30 if up else 24)
    side_h = side_n * gap
    yc = yc_band + max(side_h, gap) / 2
    bottom_y = yc + max(side_h, gap) / 2 + (BOX_H + 8)
    H = (bottom_y + BOX_H / 2 + 8) if down else (yc + max(side_h, gap) / 2 + 4)

    out = [f'<svg class="rel-ego" viewBox="0 0 {W} {H:.0f}" role="img" '
           f'aria-label="{html.escape(e["head"])} 관계도">', defs(p)]
    cw = box_w(e["head"])
    C = (xc, yc)
    edges, boxes = [], []

    def row(items, y):
        ws = [box_w(n["head"]) for n in items]
        total = sum(ws) + 12 * (len(items) - 1)
        x = xc - total / 2
        res = []
        for n, w in zip(items, ws):
            res.append((n, x + w / 2, y))
            x += w + 12
        return res

    def row_label(rp, y, s):
        x0 = min(x - box_w(n["head"]) / 2 for n, x, _ in rp)
        out.append(_label(x0 - 10, y + 4, s, "end"))

    if up:
        rp = row(up, top + BOX_H / 2)
        row_label(rp, top + BOX_H / 2, "상위")
        for n, x, y in rp:
            edges.append(_link("broader", C, cw, (x, y), box_w(n["head"]), p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))
    if down:
        rp = row(down, bottom_y)
        row_label(rp, bottom_y, "하위")
        if more_down > 0:
            x_end = max(x + box_w(n["head"]) / 2 for n, x, _ in rp)
            out.append(_label(x_end + 8, bottom_y + 4, f"+{more_down}", "start"))
        for n, x, y in rp:
            edges.append(_link("broader", (x, y), box_w(n["head"]), C, cw, p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))

    def column(items, x, side):
        y0 = yc - (len(items) - 1) * gap / 2
        for i, (kind, n) in enumerate(items):
            y = y0 + i * gap
            w = box_w(n["head"])
            if side == "left":
                edges.append(_link(kind, (x, y), w, C, cw, p))
            else:
                edges.append(_link(kind, C, cw, (x, y), w, p))
            boxes.append(node_svg(n, x, y, color=color_of(n["id"])))
        return y0

    if left:
        y0 = column(left, xl, "left")
        kinds = {k for k, _ in left}
        out.append(_label(xl, y0 - BOX_H / 2 - 8,
                          " · ".join(s for k, s in (("requires", "먼저 알 개념"), ("leads_to", "앞 단계")) if k in kinds)))
    if right:
        y0 = column(right, xr, "right")
        kinds = {k for k, _ in right}
        out.append(_label(xr, y0 - BOX_H / 2 - 8,
                          " · ".join(s for k, s in (("leads_to", "다음 단계"), ("contrasts", "혼동 주의")) if k in kinds)))
    out += edges + boxes
    out.append(node_svg(e, xc, yc, center=True, color=color_of(e["id"])))
    out.append("</svg>")
    return "".join(out)


# ── 맨 위 전체 개념 지도 ─────────────────────────────────────────

def big_node_svg(n, cx, cy, color):
    """지도 가운데 용어 — 크게 채운 알약."""
    fs, hh = 16, 36
    w = text_w(n["head"], fs) + 36
    return (f'<a class="rel-n ov-center" data-id="{html.escape(n["id"])}" href="#{html.escape(n["id"])}">'
            f'<title>{html.escape(n["head"] + " · " + n.get("en", ""))}</title>'
            f'<rect x="{cx - w / 2:.1f}" y="{cy - hh / 2:.1f}" width="{w:.1f}" height="{hh}" rx="{hh / 2}" '
            f'style="fill:{color};stroke:color-mix(in srgb, {color} 60%, #000);stroke-width:1"/>'
            f'<text x="{cx:.1f}" y="{cy + 5.5:.1f}" text-anchor="middle" font-size="{fs}" '
            f'style="fill:#fff;font-weight:700">{html.escape(n["head"])}</text></a>')


def overview_svg(layout, nodes, edges, color_of, degree):
    """layout = data/overview_layout.json (방사형). 노드·간선·묶음·주제 이름에 data-* 를 달아 JS가 강조한다."""
    p = "ov"
    W, H = layout["w"], layout["h"]
    pos = {k: tuple(v) for k, v in layout["nodes"].items() if k in nodes}
    center = set(layout.get("center") or [])
    home = dict(layout.get("home") or {})
    for c in center:
        home[c] = "center"
    # 보이는 범위는 내용(용어·주제 이름)에 맞춰 잘라 빈 여백을 없앤다
    xs = [x for x, _ in pos.values()] + [lb["x"] for lb in layout.get("labels") or []]
    ys = [y for _, y in pos.values()] + [lb["y"] for lb in layout.get("labels") or []]
    vx0, vx1 = max(0, min(xs) - 90), min(W, max(xs) + 90)
    vy0, vy1 = max(0, min(ys) - 26), min(H, max(ys) + 26)
    vb = f"{vx0:.0f} {vy0:.0f} {vx1 - vx0:.0f} {vy1 - vy0:.0f}"
    out = [f'<svg id="ovMap" class="ov-map" viewBox="{vb}" role="img" aria-label="AI 안전 개념 지도" '
           f'data-full="{vb}">', defs(p)]
    # 가운데에서 주제로 뻗는 가지 (뼈대)
    for a, b in layout.get("spine") or []:
        if a in pos and b in pos:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            d, _ = curve(x1, y1, x2, y2, 0.08)
            col = color_of(b) if b not in center else "var(--navy)"
            out.append(f'<path class="ov-spine" data-a="{a}" data-b="{b}" d="{d}" '
                       f'style="fill:none;stroke:{col};stroke-width:16;stroke-linecap:round;stroke-opacity:.09"/>')
    kids = {}
    for a, k, b in edges:
        if k == "broader" and a in pos and b in pos and home.get(a) == home.get(b):
            kids.setdefault(b, []).append(a)
    hulled = set()
    for parent, ch in sorted(kids.items(), key=lambda kv: -len(kv[1])):
        if len(ch) < 2:
            continue
        mem = [parent] + ch
        xs0 = [pos[i][0] - box_w(nodes[i]["head"]) / 2 for i in mem]
        xs1 = [pos[i][0] + box_w(nodes[i]["head"]) / 2 for i in mem]
        ys = [pos[i][1] for i in mem]
        pad = 8
        x0, x1 = min(xs0) - pad, max(xs1) + pad
        y0, y1 = min(ys) - BOX_H / 2 - pad, max(ys) + BOX_H / 2 + pad
        if x1 - x0 > 400 or y1 - y0 > 150:   # 넓게 흩어진 묶음은 영역 대신 선으로만
            continue
        hulled.update((c, parent) for c in ch)
        col = color_of(parent)
        out.append(f'<rect class="ov-hull" data-ids="{" ".join(mem)}" x="{x0:.1f}" y="{y0:.1f}" '
                   f'width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="20" '
                   f'style="fill:color-mix(in srgb, {col} 8%, transparent);'
                   f'stroke:color-mix(in srgb, {col} 34%, transparent);stroke-width:1;stroke-dasharray:4 3"/>')
    for a, k, b in edges:
        if a not in pos or b not in pos:
            continue
        if k == "broader" and (a, b) in hulled:
            continue
        cross = home.get(a) != home.get(b)
        if k == "requires":
            a, b = b, a
        wa = box_w(nodes[a]["head"]) + (40 if a in center else 0)
        wb = box_w(nodes[b]["head"]) + (40 if b in center else 0)
        svg = _link(k, pos[a], wa, pos[b], wb, p, a, b)
        if cross:
            svg = svg.replace('class="rel-e ', 'class="rel-e x-reg ', 1)
        out.append(svg)
    for i, xy in pos.items():
        if i in center:
            continue
        out.append(node_svg(nodes[i], xy[0], xy[1], color=color_of(i), hub=degree.get(i, 0) >= 6))
    for c in center:
        if c in pos:
            out.append(big_node_svg(nodes[c], pos[c][0], pos[c][1], color_of(c)))
    for lb in layout.get("labels") or []:
        tw = text_w(lb["title"], 12) + 20
        out.append(f'<g class="ov-label" data-theme="{lb["theme"]}" style="cursor:pointer">'
                   f'<rect x="{lb["x"] - tw / 2:.1f}" y="{lb["y"] - 11}" width="{tw:.1f}" height="22" rx="11" '
                   f'style="fill:var(--surface-1);stroke:var(--navy);stroke-width:1;stroke-opacity:.35"/>'
                   f'<text x="{lb["x"]}" y="{lb["y"] + 4}" text-anchor="middle" font-size="12" '
                   f'style="fill:var(--navy);font-weight:700;letter-spacing:-.01em">{html.escape(lb["title"])}</text></g>')
    out.append("</svg>")
    return "".join(out)


LEGEND_SVG = """<svg class="rel-legend" viewBox="0 0 600 24" aria-hidden="true">
<defs>
<marker id="lg-a1" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--ink-muted)"/></marker>
<marker id="lg-a2" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--text-muted);opacity:.75"/></marker>
</defs>
<path d="M4,13 Q22,5 40,13" style="fill:none;stroke:var(--ink-muted);stroke-width:1.5;opacity:.8" marker-end="url(#lg-a1)"/><text x="48" y="16" font-size="11.5" style="fill:var(--text-secondary)">이어짐</text>
<path d="M104,13 Q122,5 140,13" style="fill:none;stroke:var(--text-muted);stroke-width:1.2;opacity:.6" marker-end="url(#lg-a2)"/><text x="148" y="16" font-size="11.5" style="fill:var(--text-secondary)">먼저 알 개념 → 다음</text>
<rect x="272" y="3" width="40" height="18" rx="9" style="fill:color-mix(in srgb, var(--navy) 7%, transparent);stroke:color-mix(in srgb, var(--navy) 30%, transparent);stroke-dasharray:4 3"/><text x="320" y="16" font-size="11.5" style="fill:var(--text-secondary)">상위·하위 개념 묶음</text>
<circle cx="452" cy="12" r="7.5" style="fill:var(--surface-1);stroke:var(--accent)"/><text x="452" y="15.6" text-anchor="middle" font-size="10.5" style="fill:var(--accent);font-weight:700">≠</text><text x="466" y="16" font-size="11.5" style="fill:var(--text-secondary)">혼동 주의</text>
</svg>"""
