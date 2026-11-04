#!/usr/bin/env python3
"""인쇄본(오프라인 카드) PPTX — 샘플 카드 양식에 웹 카드(data/cards) 내용을 채운다.

  python3 scripts/build_print.py [--list 목록.json] [--template 샘플.pptx] [--out 결과.pptx]

  목록     iCloud 7_Terminology/print50.json  (비공개 — 순번·8분류·회의 표기. 공개 저장소에 넣지 않는다)
  양식     iCloud 7_Terminology/260930_AI안전용어집_AI사고보고_수정 (1).pptx  (슬라이드 1장)
  결과     iCloud 7_Terminology/YYMMDD AI안전용어집_인쇄본_검토용_vNN.pptx

내용의 정본은 웹 카드다. 인쇄본에서 문장을 고치지 말고 카드를 고친 뒤 다시 뽑는다.
칸 크기는 고정이라 글자 수로 높이를 추정해 글자 크기를 단계적으로 줄이고(설명 12.5→10pt,
기관 요점 9.5→8pt), 그래도 넘칠 것 같은 카드는 보고서(같은 이름의 _점검.md)에 적는다.
python-pptx·lxml이 필요하다(시스템 파이썬에 없으면 가상환경에서 실행).
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date

from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICLOUD = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/3_Work/3_Framework/7_Terminology")
DEF_LIST = os.path.join(ICLOUD, "print50.json")
DEF_TPL = os.path.join(ICLOUD, "260930_AI안전용어집_AI사고보고_수정 (1).pptx")
NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
EMU = 914400

# 샘플 슬라이드 도형 id
ID_NO, ID_CHAPTER, ID_HEAD, ID_EN = "4", "6", "9", "10"
ID_CAT_PILL, ID_CAT = "13", "14"
ID_DIV, ID_ALT_LBL_BG, ID_ALT_LBL, ID_ALT_PILL, ID_ALT = "15", "16", "17", "81", "19"
ID_DEF = "25"
ID_REL = "29"
FW_ROWS = [["34", "35", "36", "37", "38", "39", "40"],     # 국제(지구본·파랑)
           ["41", "42", "43", "44", "45", "46", "47"],     # 미국(초록)
           ["48", "49", "50", "51", "52", "53", "54"],     # EU(분홍)
           ["55", "56", "57", "58", "59", "60", "61"]]     # 한국(노랑, 기관명 두 줄)
FW_Y = [1.10, 2.43, 3.76, 5.09]
REF_TRIPLES = [["65", "66", "67"], ["68", "69", "70"], ["71", "72", "73"], ["74", "75", "76"]]
ID_REF_HEAD = "64"


# 8분류 색 (웹 장 리본 계열). 진한 색 하나에서 띠·알약의 연한 색을 섞어 만든다
CAT_COLORS = {"1": "0F766E", "2": "B45309", "3": "BE123C", "4": "6D28D9",
              "5": "0369A1", "6": "1D4ED8", "7": "475569", "8": "15803D"}
# 분류 색을 입힐 도형: id → 샘플 색 → 역할(deep/band/pill)
PAINT = {"3": {"1F3A68": "deep"}, "2": {"EAF1FA": "band"}, "6": {"2A3A55": "deep"}, "8": {"1F3A68": "deep"},
         "11": {"2F5DA8": "deep"}, "13": {"DCE8F7": "pill"}, "14": {"2F5DA8": "deep"},
         "16": {"2F5DA8": "deep"}, "81": {"DCE8F7": "pill"}, "27": {"2F5DA8": "deep"}}


def tint(hexc: str, a: float) -> str:
    """흰색 위에 hexc를 a만큼 섞은 색."""
    rgb = [int(hexc[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(255 - (255 - v) * a):02X}" for v in rgb)


def paint(root, cat_no: str):
    deep = CAT_COLORS.get(str(cat_no))
    if not deep:
        return
    role = {"deep": deep, "band": tint(deep, 0.09), "pill": tint(deep, 0.16)}
    for sid, m in PAINT.items():
        sp = sp_by_id(root, sid)
        if sp is None:
            continue
        for c in sp.iter("{%s}srgbClr" % NS["a"]):
            if c.get("val", "").upper() in m:
                c.set("val", role[m[c.get("val").upper()]])


# 조지연 연구원 요청(2026-11-04): 인쇄본은 마침표를 빼고 '~함'을 명사로 끝낸다. 웹 카드는 문장 그대로 둔다.
NOUN_END = ("의미 정의 설명 제시 지적 권고 구분 소개 포함 요구 예시 정리 규정 포괄 구별 명시 평가 측정 활용 제외 이용 연결 "
            "기록 판단 대응 통칭 식별 시도 강조 제안 표시 판정 분류 구성 적용 언급 인용 반영 추정 보고").split()


def gaejo(t):
    """'…설명함.' → '…설명'. 괄호로 끝나면 괄호 앞을 본다. 명사로 끝낼 수 없는 어미(있음·봄·말함 등)는 마침표만 뺀다."""
    t = t.strip().rstrip(".")
    m = re.search(r"([가-힣]+)함(\([^()]*\))?$", t)
    if m:
        for w in NOUN_END:
            if m.group(1).endswith(w) and (len(m.group(1)) == len(w) or not m.group(1).endswith("아니" + w)):
                return t[:m.start()] + m.group(1) + (m.group(2) or "")
    return t


def shown_pages(r):
    """출처에 붙일 쪽수: 인쇄 쪽(pages_printed)이 있으면 그것, 없으면 색인의 물리 쪽. 한국 법령은 조문으로 인용해 쪽수를 달지 않는다."""
    if r.get("text", "").startswith("「"):
        return None
    ev = r.get("evidence") or {}
    return ev.get("pages_printed") or ev.get("pages")


def org_row(org: str) -> int:
    if "EU" in org or "유럽" in org:
        return 2
    if any(k in org for k in ("NIST", "미국")):
        return 1
    if any(k in org for k in ("한국", "과기정통부", "기본법", "가이드라인", "윤리원칙", "프레임워크")):
        return 3
    return 0  # 국제·영국·기타는 지구본 행


def nospace(s): return re.sub(r"\s+", "", s or "")


def text_w(s: str, pt: float) -> float:
    """대략적인 글자 폭(인치)."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or ch in "「」·“”‘’":
            w += 1.0
        elif ch == " ":
            w += 0.3
        elif ch.isupper() or ch.isdigit():
            w += 0.62
        else:
            w += 0.52
    return w * pt / 72


def est_height(paras, pt, width, line=1.15, after_pt=10, indent=0.19, slack=1.08):
    """줄바꿈은 단어 단위라 실제 줄 수가 더 많다 — slack만큼 넉넉히 잡는다."""
    h = 0.0
    for p in paras:
        lines = max(1, math.ceil(text_w(p, pt) * slack / (width - indent)))
        h += lines * pt * line / 72 + after_pt / 72
    return h


# ── XML 도우미 ───────────────────────────────────────────────────

def sp_by_id(root, sid):
    r = root.xpath(f".//p:sp[p:nvSpPr/p:cNvPr/@id='{sid}'] | .//p:pic[p:nvPicPr/p:cNvPr/@id='{sid}']", namespaces=NS)
    return r[0] if r else None


def xfrm(el):
    x = el.find("./p:spPr/a:xfrm", NS)
    return x


def set_box(el, x=None, y=None, w=None, h=None):
    xf = xfrm(el)
    off, ext = xf.find("a:off", NS), xf.find("a:ext", NS)
    if x is not None: off.set("x", str(int(x * EMU)))
    if y is not None: off.set("y", str(int(y * EMU)))
    if w is not None: ext.set("cx", str(int(w * EMU)))
    if h is not None: ext.set("cy", str(int(h * EMU)))


def get_box(el):
    xf = xfrm(el)
    off, ext = xf.find("a:off", NS), xf.find("a:ext", NS)
    return (int(off.get("x")) / EMU, int(off.get("y")) / EMU, int(ext.get("cx")) / EMU, int(ext.get("cy")) / EMU)


def set_text(sp, text, sz=None):
    """첫 문단·첫 run의 서식을 살려 한 문단짜리 글로 바꾼다."""
    tb = sp.find("p:txBody", NS)
    ps = tb.findall("a:p", NS)
    p0 = ps[0]
    for p in ps[1:]:
        tb.remove(p)
    runs = p0.findall("a:r", NS)
    for r in runs[1:]:
        p0.remove(r)
    runs[0].find("a:t", NS).text = text
    if sz:
        for rpr in p0.iter("{%s}rPr" % NS["a"], "{%s}endParaRPr" % NS["a"]):
            rpr.set("sz", str(int(sz * 100)))


def set_paras(sp, items, sz=None, model_idx=None):
    """items = [(model_paragraph_index, [ (text, model_run_index), ... ]), ...] — 샘플 문단을 복제해 채운다."""
    tb = sp.find("p:txBody", NS)
    models = tb.findall("a:p", NS)
    models = [copy.deepcopy(p) for p in models]
    for p in tb.findall("a:p", NS):
        tb.remove(p)
    for mi, runs in items:
        p = copy.deepcopy(models[min(mi, len(models) - 1)])
        mruns = p.findall("a:r", NS)
        mruns_c = [copy.deepcopy(r) for r in mruns]
        for r in mruns:
            p.remove(r)
        end = p.find("a:endParaRPr", NS)
        for txt, ri in runs:
            r = copy.deepcopy(mruns_c[min(ri, len(mruns_c) - 1)])
            t = r.find("a:t", NS)
            t.text = txt
            if txt != txt.strip():
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            if end is not None:
                end.addprevious(r)
            else:
                p.append(r)
        if sz:
            for rpr in p.iter("{%s}rPr" % NS["a"], "{%s}endParaRPr" % NS["a"]):
                rpr.set("sz", str(int(sz * 100)))
        tb.append(p)


def remove(el):
    if el is not None and el.getparent() is not None:
        el.getparent().remove(el)


REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
HLINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"


def in_print_order(card):
    """기관 행을 국제·미국·EU·한국 순으로 놓고, 출처 번호를 본문 등장 순서로 다시 매긴 사본을 돌려준다."""
    c = copy.deepcopy(card)
    c["frameworks"] = sorted(c.get("frameworks") or [], key=lambda f: org_row(f["org"]))
    old = {r["n"]: r for r in c.get("refs") or []}
    new, seen = [], {}
    for f in c["frameworks"]:
        for p in f.get("points") or []:
            ns = []
            for n in p.get("refs") or []:
                if n not in seen:
                    seen[n] = len(new) + 1
                    new.append({**old[n], "n": seen[n]})
                ns.append(seen[n])
            p["refs"] = sorted(ns)
    c["refs"] = new
    return c


def clean_alts(item, card, head):
    """대체어: 표제어 반복을 빼고, 'X(Y)' 꼴 회의 표기는 Y만 남기며, alt_drop에 적은 것은 뺀다."""
    drop = {nospace(x) for x in item.get("alt_drop") or []}
    alts = []
    m = (item.get("meeting") or "").strip()
    g = re.fullmatch(r"(.+?)\((.+)\)", m)
    if nospace(m) in drop:
        m = ""
    elif g and nospace(g.group(1)) == nospace(head):
        m = g.group(2)
    for a in [m] + [x["text"] for x in card.get("alternatives") or []]:
        if a and nospace(a) != nospace(head) and nospace(a) not in drop and nospace(a) not in {nospace(x) for x in alts}:
            alts.append(a)
    return alts


# ── 카드 → 슬라이드 ──────────────────────────────────────────────

def fill_slide(root, item, card, entry, cat, warns, next_id, links):
    head = card["head"]
    card = in_print_order(card)
    paint(root, cat["no"])
    set_text(sp_by_id(root, ID_NO), f"{item['no']:03d}")
    set_text(sp_by_id(root, ID_CHAPTER), f"{int(cat['no']):02d}. {cat['label']} ({cat['en']})")
    set_text(sp_by_id(root, ID_HEAD), head, sz=32 if text_w(head, 32) < 5.8 else 26)
    en = card["en"]
    esz = next((z for z in (20, 17, 15, 13) if text_w(en, z) <= 5.8), 12)   # 긴 영문은 한 줄에 맞춘다
    set_text(sp_by_id(root, ID_EN), en, sz=esz)

    # 구분 · 대체어 (폭을 글자에 맞춰 늘리고 뒤 요소를 민다)
    cat_label = item.get("chip") or entry["category_label"]
    cat_w = max(1.17, text_w(cat_label, 10.5) + 0.3)
    set_box(sp_by_id(root, ID_CAT_PILL), w=cat_w)
    set_box(sp_by_id(root, ID_CAT), w=cat_w)
    set_text(sp_by_id(root, ID_CAT), cat_label)
    alts = clean_alts(item, card, head)
    x_div = 0.98 + cat_w + 0.13
    if not alts:
        for sid in (ID_DIV, ID_ALT_LBL_BG, ID_ALT_LBL, ID_ALT_PILL, ID_ALT):
            remove(sp_by_id(root, sid))
    else:
        set_box(sp_by_id(root, ID_DIV), x=x_div)
        set_box(sp_by_id(root, ID_ALT_LBL_BG), x=x_div + 0.13)
        set_box(sp_by_id(root, ID_ALT_LBL), x=x_div + 0.13)
        vx = x_div + 0.13 + 0.79 + 0.10
        room = 6.36 - vx
        shown = []
        for a in alts:
            if text_w(" · ".join(shown + [a]), 9.5) + 0.3 <= room:
                shown.append(a)
        if not shown:
            shown = [alts[0]]
        if len(shown) < len(alts):
            warns.append(f"대체어 일부 생략: {', '.join(a for a in alts if a not in shown)}")
        s = " · ".join(shown)
        vw = min(room, text_w(s, 9.5) + 0.3)
        pill = sp_by_id(root, ID_ALT_PILL)
        px, py, pw, ph = get_box(pill)
        set_box(pill, x=vx, w=vw)
        set_box(sp_by_id(root, ID_ALT), x=vx, y=py, w=vw, h=ph)
        set_text(sp_by_id(root, ID_ALT), s)

    # 용어 설명: 정의(•·굵게) + 부연·구별(-)
    d = card.get("definition") or {}
    paras = [d.get("lead") or ""] + list(d.get("points") or [])
    dist = (d.get("distinction") or {}).get("text")
    if dist:
        paras.append(dist)
    paras = [gaejo(p) for p in paras]
    defbox = sp_by_id(root, ID_DEF)
    set_box(defbox, y=2.86, h=3.02)          # 제목 아래 빈 공간까지 올려 쓴다 (구분선 5.95 위에서 끝남)
    box_h = 2.74   # 렌더 실측으로 맞춘 값 (구분선 5.95 위에서 끝남)
    size = 12.5
    for s_ in (12.5, 12, 11.5, 11, 10.5, 10):
        size = s_
        if est_height(paras, s_, 6.06, after_pt=10 * s_ / 12.5) <= box_h:
            break
    else:
        warns.append(f"용어 설명이 칸을 넘칠 수 있음(10pt에서도) — {sum(len(p) for p in paras)}자")
    items = [(0, [(paras[0], 0)])] + [(1, [(p, 0)]) for p in paras[1:]]
    set_paras(sp_by_id(root, ID_DEF), items, sz=size)

    # 관련 용어
    tags = []
    for r in entry.get("related") or []:
        t = "#" + nospace(r.get("head") or r.get("label") or "")
        if text_w("   ".join(tags + [t]), 10.5) <= 5.8:
            tags.append(t)
    set_text(sp_by_id(root, ID_REL), "   ".join(tags) if tags else "—")

    # 기관·문서별 개념: 유형에 맞는 샘플 행을 복제해 칸 수만큼
    rows_tpl = []
    anchor = sp_by_id(root, FW_ROWS[0][0])
    parent = anchor.getparent()
    insert_at = parent.index(anchor)
    for r in FW_ROWS:
        rows_tpl.append([copy.deepcopy(sp_by_id(root, sid)) for sid in r])
    for r in FW_ROWS:
        for sid in r:
            remove(sp_by_id(root, sid))
    fws = card["frameworks"]
    if len(fws) > 4:
        warns.append(f"기관 {len(fws)}개 중 4개만 실음: 뺀 것 {', '.join(f['org'] for f in fws[4:])}")
        fws = fws[:4]
    placeholder = not fws
    if placeholder:
        fws = [{"org": "보강 필요", "sub": "", "points": [{"text": "확인된 기관·문서별 정의·적용 근거가 아직 없음. 검토 때 근거(문서·쪽수)를 보강해 주십시오.", "refs": []}]}]
    for j, f in enumerate(fws):
        t = org_row(f.get("org", "")) if not placeholder else 0
        els = [copy.deepcopy(e) for e in rows_tpl[t]]
        dy = FW_Y[j] - FW_Y[t]
        for e in els:
            x, y, w, h = get_box(e)
            set_box(e, y=y + dy)
            for nv in e.iter("{%s}cNvPr" % NS["p"]):
                nv.set("id", str(next_id[0])); next_id[0] += 1
        bg, lbg, div, pic, org_el, sub_el, pts_el = els
        org = f.get("org", "")
        words = org.split()
        two = text_w(org, 12.5) > 1.22
        if two:   # 두 줄: 가운데에 가까운 띄어쓰기에서 나눈다
            best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:])))) if len(words) > 1 else 1
            lines = [" ".join(words[:best]), " ".join(words[best:])] if len(words) > 1 else [org]
        else:
            lines = [org]
        osz = 12.5
        while max(text_w(l, osz) for l in lines) > 1.24 and osz > 9:
            osz -= 0.5
        set_paras(org_el, [(0, [(l, 0)]) for l in lines], sz=osz)
        ry = FW_Y[j]
        if len(lines) == 2:
            set_box(pic, y=ry + 0.08); set_box(org_el, y=ry + 0.45, h=0.50); set_box(sub_el, y=ry + 0.97)
        else:
            set_box(pic, y=ry + 0.20); set_box(org_el, y=ry + 0.59, h=0.25); set_box(sub_el, y=ry + 0.84)
        sub = str(f.get("sub") or "")
        sub = f"({sub})" if sub and not sub.startswith("(") else sub
        ssz = next((z for z in (10.5, 10, 9.5, 9, 8.5, 8) if text_w(sub, z) <= 1.26), 8)
        set_text(sub_el, sub, sz=ssz)
        if placeholder:
            remove(pic)
        pts = []
        for p in f.get("points") or []:
            txt = gaejo(p["text"] if isinstance(p, dict) else p)
            refs = p.get("refs") if isinstance(p, dict) else []
            runs = [(txt, 0)]
            if refs:
                runs.append((" " + "".join(f"[{n}]" for n in refs), 1))
            pts.append(runs)
        flat = ["".join(r[0] for r in rs) for rs in pts]
        psz = 9.5
        for s_ in (9.5, 9, 8.5, 8):
            psz = s_
            if est_height(flat, s_, 5.01, line=1.05, after_pt=3, indent=0.17) <= 1.12:
                break
        else:
            warns.append(f"기관 요점이 칸을 넘칠 수 있음: {org}")
        set_paras(pts_el, [(0, rs) for rs in pts], sz=psz)
        for k, e in enumerate(els):
            if e is pic and placeholder:
                continue
            parent.insert(insert_at + j * 7 + k, e)
    if placeholder:
        warns.append("기관·문서별 개념 없음 — 보강 필요")

    # 출처: 번호 원 + 번호 + 서지, 4개를 넘으면 줄 간격을 줄인다
    tri_tpl = [copy.deepcopy(sp_by_id(root, sid)) for sid in REF_TRIPLES[0]]
    anchor = sp_by_id(root, REF_TRIPLES[0][0])
    rparent = anchor.getparent()
    r_at = rparent.index(anchor)
    for tri in REF_TRIPLES:
        for sid in tri:
            remove(sp_by_id(root, sid))
    refs = card.get("refs") or []
    if not refs:
        warns.append("출처 없음")
    step = 0.15 if len(refs) <= 4 else max(0.105, 0.72 / (len(refs) - 1))
    for k, r in enumerate(refs):
        els = [copy.deepcopy(e) for e in tri_tpl]
        for e in els:
            x, y, w, h = get_box(e)
            set_box(e, y=y + k * step)
            for nv in e.iter("{%s}cNvPr" % NS["p"]):
                nv.set("id", str(next_id[0])); next_id[0] += 1
        txt = r.get("text", "")
        pages = shown_pages(r)
        if pages and pages not in txt:
            txt += f", {pages}"
        if r.get("url"):  # 서지 글상자 전체에 원문 링크 (글자 서식은 그대로)
            rid = f"rIdRef{k + 1}"
            links.append((rid, r["url"]))
            nv = els[2].find(".//p:cNvPr", NS)
            etree.SubElement(nv, "{%s}hlinkClick" % NS["a"]).set("{%s}id" % NS["r"], rid)
        set_text(els[1], str(r.get("n", k + 1)))
        rsz = 7.5 if text_w(txt, 7.5) <= 5.04 else 7 if text_w(txt, 7) <= 5.04 else 6.5
        if text_w(txt, rsz) > 5.04:
            warns.append(f"출처 [{r.get('n')}] 서지가 한 줄을 넘음")
        set_text(els[2], txt, sz=rsz)
        for i_, e in enumerate(els):
            rparent.insert(r_at + k * 3 + i_, e)
    if len(refs) > 6:
        warns.append(f"출처 {len(refs)}개 — 칸이 빠듯함")


NOTES_PAGE = [
    "기준일: 법령과 문서의 현황은 2026.11.4 기준",
    "구성: 맨 위 분류(01~08)는 인쇄본의 8개 분류이고, '구분'은 온라인 용어집의 4개 대분류(기술·역량, 위험·사고, 평가·안전 대책, 거버넌스·제도)임. 두 체계는 서로 다른 기준이라 같은 분류 안에서도 구분이 다를 수 있음",
    "표제어: AI 안전 번역 용어 정본을 따르고 AI를 붙이지 않음. 예외는 AI를 빼면 뜻이 달라지는 용어. 영문 표제어도 같은 원칙에 단수·미국식 철자로 적음",
    "대체어: 표제어와 다른 역어·음차어만 적음",
    "위험과 피해: risk는 '위험', harm은 '피해', hazard는 '위험원'으로 통일함. 인공지능기본법과 가이드라인의 용례에 맞춰 '리스크'를 쓰지 않음",
    "관련 용어(#): 이 인쇄본에 없는 용어는 온라인 용어집에서 찾을 수 있음(songkyungho.github.io/ai-safety-glossary)",
    "법령 이름: 본문은 'EU AI법', 기관 칸과 출처는 'EU AI Act'로 적음. 「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」은 '인공지능기본법' 또는 '한국 AI 기본법'으로 줄임",
    "쪽 번호: 출처의 쪽 번호는 문서에 인쇄된 번호임. 한국 법령은 조문으로, EU AI Act는 조문과 관보(OJ L, 2024/1689) 쪽으로 적음",
    "국제 AI 안전 보고서: 영문판을 기준으로 하고, 한국어 번역 표현을 인용할 때만 한국어판을 씀",
    "EU AI법 적용일: 옴니버스 규정(Regulation (EU) 2026/1744, 2026.7.27 발효)으로 고위험 요건(제3장 제1~3절) 적용일이 부속서 III 시스템 2027.12.2, 부속서 I 시스템 2028.8.2로 늦춰짐",
    "NIST AI 800-1: 2차 공개 초안(2025.1) 기준이며 최종본이 아님. 이 초안의 근거였던 행정명령 14110은 2025.1.20 폐지됨",
    "UK AISI: 인용 문서를 낸 2025년 2월 초의 이름은 AI Safety Institute이고, 2025.2.14 AI Security Institute로 이름을 바꿈",
]


def fill_notes_page(root):
    """마지막 장 일러두기: 샘플 슬라이드에서 머리 띠만 남기고 설명 글상자를 넓혀 쓴다."""
    keep = {"2", "3", "4", "5", "6", "7"}
    box = sp_by_id(root, ID_DEF)
    tree_ = box.getparent()
    set_text(sp_by_id(root, ID_NO), "안내")
    set_text(sp_by_id(root, ID_CHAPTER), "일러두기")
    set_box(sp_by_id(root, "7"), w=12.73)
    for el in list(tree_):
        if etree.QName(el).localname not in ("sp", "pic", "cxnSp", "grpSp", "graphicFrame"):
            continue   # nvGrpSpPr·grpSpPr는 슬라이드 필수 요소라 지우면 PowerPoint가 복구를 요구한다
        nv = el.find(".//p:cNvPr", NS)
        if nv is not None and nv.get("id") not in keep and nv.get("id") != ID_DEF:
            tree_.remove(el)
    set_box(box, x=0.45, y=0.8, w=12.43, h=6.4)
    bp = box.find("p:txBody/a:bodyPr", NS)
    bp.set("numCol", "2"); bp.set("spcCol", str(int(0.35 * EMU)))
    set_paras(box, [(1, [(t, 0)]) for t in NOTES_PAGE], sz=12)


def clear_notes(unp):
    """샘플 슬라이드의 발표자 노트가 복제본에 남지 않게 비운다."""
    for path in glob.glob(os.path.join(unp, "ppt", "notesSlides", "*.xml")):
        t = etree.parse(path)
        for e in t.getroot().iter("{%s}t" % NS["a"]):
            e.text = ""
        t.write(path, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=DEF_LIST)
    ap.add_argument("--template", default=DEF_TPL)
    ap.add_argument("--out", default=None)
    ap.add_argument("--add-slide", default=None, help="pptx 스킬의 add_slide.py 경로")
    args = ap.parse_args()

    lst = json.load(open(args.list, encoding="utf-8"))
    cats = {c["no"]: c for c in lst["categories"]}
    cards = {json.load(open(p))["id"]: json.load(open(p)) for p in glob.glob(os.path.join(ROOT, "data", "cards", "*.json"))}
    site = json.load(open(os.path.join(ROOT, "data", "glossary_site.json"), encoding="utf-8"))
    entries = {e["id"]: e for e in site["entries"]}
    items = lst["items"]
    missing = [i["id"] for i in items if i["id"] not in cards or i["id"] not in entries]
    if missing:
        sys.exit(f"카드·사이트 데이터에 없는 용어: {missing} — apply_editorial.py를 먼저 돌리세요")

    out = args.out
    if not out:
        stamp = date.today().strftime("%y%m%d")
        v = 1
        while True:
            out = os.path.join(ICLOUD, f"{stamp} AI안전용어집_인쇄본_검토용_v{v:02d}.pptx")
            if not os.path.exists(out):
                break
            v += 1
    work = tempfile.mkdtemp(prefix="print_")
    unp = os.path.join(work, "u")
    zipfile.ZipFile(args.template).extractall(unp)
    # 구조 먼저: 슬라이드 1장을 목록 수만큼 복제
    add_slide = args.add_slide
    for k in range(1, len(items) + 1):   # 마지막 한 장은 일러두기 (슬라이드 번호 = 카드 번호 유지)
        subprocess.run([sys.executable, add_slide, unp, "slide1.xml", "--after", f"slide{k}.xml"],
                       check=True, capture_output=True)
    pres = etree.parse(os.path.join(unp, "ppt", "presentation.xml"))
    rels = etree.parse(os.path.join(unp, "ppt", "_rels", "presentation.xml.rels")).getroot()
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    order = [rid2t[s.get("{%s}id" % NS["r"])] for s in pres.getroot().find("p:sldIdLst", NS)]

    report = []
    for item, target in zip(items, order):
        path = os.path.join(unp, "ppt", target)
        tree = etree.parse(path)
        root = tree.getroot()
        next_id = [1000]
        warns = []
        card, entry = cards[item["id"]], entries[item["id"]]
        links = []
        fill_slide(root, item, card, entry, cats[item["cat"]], warns, next_id, links)
        tree.write(path, xml_declaration=True, encoding="UTF-8", standalone=True)
        if links:
            rpath = os.path.join(os.path.dirname(path), "_rels", os.path.basename(path) + ".rels")
            rt = etree.parse(rpath)
            for rid, url in links:
                etree.SubElement(rt.getroot(), "{%s}Relationship" % REL_NS, Id=rid, Type=HLINK, Target=url, TargetMode="External")
            rt.write(rpath, xml_declaration=True, encoding="UTF-8", standalone=True)
        report.append((item, card, warns))

    path = os.path.join(unp, "ppt", order[len(items)])
    tree = etree.parse(path)
    fill_notes_page(tree.getroot())
    tree.write(path, xml_declaration=True, encoding="UTF-8", standalone=True)
    clear_notes(unp)
    for t_ in order:   # 구조 점검: 여기서 어긋나면 PowerPoint가 복구를 요구한다
        r_ = etree.parse(os.path.join(unp, "ppt", t_)).getroot()
        kids = [etree.QName(k).localname for k in r_.find("p:cSld/p:spTree", NS)]
        ids = [e.get("id") for e in r_.iter("{%s}cNvPr" % NS["p"])]
        if kids[:2] != ["nvGrpSpPr", "grpSpPr"] or len(ids) != len(set(ids)):
            sys.exit(f"슬라이드 구조 오류: {t_}")

    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(unp):
            for f in files:
                full = os.path.join(base, f)
                z.write(full, os.path.relpath(full, unp))
    shutil.rmtree(work)

    rep = os.path.splitext(out)[0] + "_점검.md"
    with open(rep, "w", encoding="utf-8") as fh:
        fh.write(f"# 인쇄본 점검 — {os.path.basename(out)}\n\n")
        fh.write(f"용어 {len(items)}개 · 생성 {date.today().isoformat()} · 내용 정본: 웹 카드(data/cards)\n\n")
        fh.write("| 번호 | 분류 | 표제어 | 상태 | 기관 수 | 확인할 것 |\n|---|---|---|---|---|---|\n")
        for item, card, warns in report:
            fh.write(f"| {item['no']:03d} | {item['cat']} | {card['head']} | {card.get('status', '')} | "
                     f"{len(card.get('frameworks') or [])} | {'; '.join(warns) or '—'} |\n")
    print(f"{len(items)}장 → {out}\n점검표 → {rep}")


if __name__ == "__main__":
    main()
