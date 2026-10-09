#!/usr/bin/env python3
"""docs/rel.js 와 카드 안 관계도 점검 (표준 라이브러리만).

  python3 scripts/tests/test_rel_js.py

확인하는 것
  1. docs/rel.js 가 `window.__REL__=<JSON>;` 꼴이고 JSON 으로 읽힌다.
  2. 관계 이웃이 있는 표제어(relmap.ego_layout 이 None 이 아닌 것) 모두 rel.js 의 t 에 있고,
     카드의 <div class="rel-mount" data-rel="…"> 와 1:1 로 맞는다. 쓰인 노드는 모두 n 에 있다.
  3. docs/index.html 안에 카드별 <svg class="rel-ego"> 가 더는 없고, 맨 위 전체 지도(ovMap)는 남아 있다.
  4. (node 가 있으면) 페이지의 drawEgo(JS) 가 그린 SVG 와 relmap.ego_svg(파이썬) 가 같은지 —
     좌표는 rel.js 에서 소수 1자리로 줄였으므로 숫자는 0.11 안에서, 개행을 뺀 나머지 글자는 그대로 비교한다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config  # noqa: E402
import relmap  # noqa: E402

NUM = re.compile(r"-?\d+(?:\.\d+)?")


def load_rel_js(path):
    src = open(path, encoding="utf-8").read()
    m = re.match(r"window\.__REL__=(.*?);\nif\(window\.__onRel__\)window\.__onRel__\(\);\n$", src, re.S)
    assert m, "rel.js 꼴이 다르다: window.__REL__=…; 뒤에 __onRel__ 호출이 와야 한다"
    return json.loads(m.group(1))


def same_svg(a, b, tol=0.11):
    """숫자만 tol 안에서, 줄바꿈(파이썬 defs 의 개행)은 무시, 나머지는 그대로."""
    a, b = a.replace("\n", ""), b.replace("\n", "")
    if NUM.sub("#", a) != NUM.sub("#", b):
        return False
    na, nb = NUM.findall(a), NUM.findall(b)
    return len(na) == len(nb) and all(abs(float(x) - float(y)) <= tol for x, y in zip(na, nb))


def main():
    index = os.path.join(config.DOCS, "index.html")
    rel_path = os.path.join(config.DOCS, "rel.js")
    data = json.load(open(os.path.join(config.DATA, "glossary_site.json"), encoding="utf-8"))
    ents = data["entries"]
    nodes = {e["id"]: {"id": e["id"], "head": e["head"], "en": e["en"]} for e in ents}
    color = {e["id"]: e["color"] for e in ents}
    color_of = lambda i: color.get(i, "var(--navy)")

    rel = load_rel_js(rel_path)
    assert set(rel) == {"n", "t"}, "rel.js 최상위 키는 n, t"
    expect = {e["id"] for e in ents if relmap.ego_layout(e, nodes)}
    got = set(rel["t"])
    assert got == expect, "rel.js 항목 불일치: 빠짐 %s / 남음 %s" % (sorted(expect - got)[:5], sorted(got - expect)[:5])
    for tid, lay in rel["t"].items():
        assert set(lay) == {"w", "h", "c", "n", "e", "l"}, tid
        assert lay["c"][0] == tid and lay["c"][0] in rel["n"], tid
        for b in lay["n"]:
            assert b[0] in rel["n"], "n 에 없는 노드 %s (%s)" % (b[0], tid)
        for ed in lay["e"]:
            assert ed[0] in relmap.EDGE_KIND and len(ed) == 5, (tid, ed)
        for lb in lay["l"]:
            assert len(lb) == 4 and lb[3] in ("start", "middle", "end"), (tid, lb)

    html = open(index, encoding="utf-8").read()
    mounts = re.findall(r'<div class="rel-scroll rel-mount" data-rel="([^"]+)">', html)
    assert len(mounts) == len(set(mounts)) and set(mounts) == expect, "카드의 rel-mount 와 rel.js 가 다르다"
    assert not re.search(r'<svg class="rel-ego" viewBox="0 0 \d', html), "index.html 에 카드별 rel-ego SVG 가 남아 있다"
    assert '<svg id="ovMap"' in html, "맨 위 전체 지도가 없다"
    assert '<script defer src="rel.js"></script>' in html and "window.drawEgo = function" in html
    print("rel.js %d개 관계도 · 노드 %d · index.html 카드 SVG 0개 · 전체 지도 유지 — OK"
          % (len(rel["t"]), len(rel["n"])))

    node = shutil.which("node")
    if not node:
        print("node 없음 — JS 그리기 대조는 건너뜀")
        return
    m = re.search(r"<script>\n/\* 카드 안 관계도.*?</script>", html, re.S)
    assert m, "EGO_JS 블록을 찾지 못했다"
    js_code = m.group(0)[len("<script>"):-len("</script>")]
    harness = (open(rel_path, encoding="utf-8").read().replace("if(window.__onRel__)window.__onRel__();", "")
               + "\n" + js_code
               + "\nvar out={};for(var id in window.__REL__.t){var el={};window.drawEgo(id,el);out[id]=el.innerHTML;}"
               "process.stdout.write(JSON.stringify(out));")
    r = subprocess.run([node, "-e", "var window=globalThis;" + harness], capture_output=True, text=True, check=True)
    js_out = json.loads(r.stdout)
    bad = []
    for e in ents:
        if e["id"] not in expect:
            continue
        py = relmap.ego_svg(e, nodes, color_of)
        if not same_svg(py, js_out[e["id"]]):
            bad.append(e["id"])
    assert not bad, "JS 와 파이썬 그림이 다른 용어: %s" % bad[:10]
    print("node 대조: %d개 관계도 모두 JS == 파이썬 (숫자 ±0.11) — OK" % len(expect))


if __name__ == "__main__":
    main()
