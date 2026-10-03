#!/usr/bin/env python3
"""정적 사이트 생성 — docs/index.html · docs/about.html.

지면 토큰·내비게이션은 ui_common(= AI 안전 라이브러리와 동일)에서 온다.
입력은 apply_editorial.py가 만든 data/glossary_site.json (병합본 + 카드 편집 계층).
카드·필터 칩 스타일도 라이브러리 EXTRA_CSS 어휘를 따른다.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import ui_common as ui  # noqa: E402
import relmap  # noqa: E402

KST = timezone(timedelta(hours=9))

GLOSSARY_CSS = """
/* 지면 토큰은 ui_common.NAV_CSS(:root) — 라이브러리와 같은 팔레트 */
a { color: var(--sage); }
a:hover { color: var(--accent); }
.wrap { max-width: 980px; }

#listControls { margin: 0 0 18px; }
.filter-toolbar {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--hairline);
}
#listControls .filter-toolbar:first-child { padding-top: 0; }
#listControls .filter-toolbar:last-child { border-bottom: 0; }
.filter-label {
  flex: 0 0 auto; min-width: 3.2em; margin-right: 4px;
  font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em; white-space: nowrap;
}
button.filter-chip {
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid var(--hairline); background: transparent;
  color: var(--text-secondary); border-radius: 999px;
  padding: 3px 10px; font: inherit; font-size: 0.75rem; line-height: 1.35;
  cursor: pointer; white-space: nowrap;
}
button.filter-chip:hover { color: var(--ink); border-color: var(--text-muted); }
button.filter-chip .n {
  font-variant-numeric: tabular-nums; color: var(--text-muted); font-size: 0.75rem;
}
button.filter-chip.active {
  background: color-mix(in srgb, var(--chip, var(--navy)) 14%, var(--surface-1));
  color: var(--chip, var(--navy));
  border-color: color-mix(in srgb, var(--chip, var(--navy)) 32%, var(--hairline));
  font-weight: 600;
}
button.filter-chip.active .n {
  color: color-mix(in srgb, var(--chip, var(--navy)) 65%, var(--text-muted));
}

.result-line {
  font-size: 0.75rem; color: var(--text-muted); margin: 0 0 12px;
  font-variant-numeric: tabular-nums;
}
.bucket-head {
  font-size: 0.95rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--text-muted); margin: 22px 0 8px; padding-bottom: 6px;
  border-bottom: 1px solid var(--gridline);
}
.bucket-head:first-of-type { margin-top: 4px; }
.bucket-head .bk { color: var(--chip); }

.term-card {
  background: var(--surface-1); border: 1px solid var(--hairline);
  border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
  border-left: 3px solid var(--chip);
}
.term-card.hidden { display: none; }
.term-head {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline;
}
.term-n {
  font-variant-numeric: tabular-nums; font-size: 0.75rem;
  color: var(--text-muted); min-width: 2.2em;
}
.term-name {
  font-size: 1.05rem; font-weight: 700; letter-spacing: -0.03em; color: var(--ink);
}
.term-alt {
  font-weight: 500; font-size: 1rem; color: var(--text-muted);
  letter-spacing: -0.01em;
}
.term-en {
  font-size: 0.95rem; color: var(--text-muted); letter-spacing: -0.01em;
}
.badge {
  margin-left: auto; font-size: 0.75rem; font-weight: 600; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap;
  background: color-mix(in srgb, var(--chip) 14%, var(--surface-1));
  color: var(--chip);
  border: 1px solid color-mix(in srgb, var(--chip) 32%, var(--hairline));
}
.source-chips {
  display: flex; flex-wrap: wrap; gap: 5px; margin-left: auto;
}
.source-chip {
  font-size: 0.75rem; font-weight: 700; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap; letter-spacing: -0.02em;
  border: 1px solid var(--hairline);
}
.source-chip.digest {
  color: var(--navy);
  background: color-mix(in srgb, var(--navy) 12%, var(--surface-1));
  border-color: color-mix(in srgb, var(--navy) 28%, var(--hairline));
}
.source-chip.pdf {
  color: #8b4518;
  background: color-mix(in srgb, #c45c48 12%, var(--surface-1));
  border-color: color-mix(in srgb, #c45c48 30%, var(--hairline));
}
.source-chip.both {
  color: var(--ink);
  background: color-mix(in srgb, var(--gold) 18%, var(--surface-1));
  border-color: color-mix(in srgb, var(--gold) 40%, var(--hairline));
}
.section-label {
  margin: 12px 0 6px; font-size: 0.75rem; font-weight: 700;
  color: var(--text-muted); letter-spacing: -0.02em;
}
.section-label:first-child { margin-top: 10px; }
.quote-block {
  margin-top: 8px; padding: 12px 14px;
  background: var(--surface-2); border-radius: 10px;
  border: 1px solid var(--gridline);
}
.quote-block + .quote-block { margin-top: 8px; }
.quote-ko {
  margin: 0 0 8px; font-size: 1rem; line-height: 1.72;
  color: var(--ink); letter-spacing: -0.02em; font-weight: 500;
}
.quote-ko .ko-label {
  display: inline-block; margin-right: 6px;
  font-size: 0.68rem; font-weight: 700;
  color: var(--navy);
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
.quote-text {
  margin: 0; font-size: 0.95rem; line-height: 1.7;
  color: var(--ink-muted); letter-spacing: -0.01em;
}
.quote-cite {
  margin: 8px 0 0; font-size: 0.75rem; color: var(--text-muted); line-height: 1.5;
}
.quote-cite .cite-label {
  display: inline-block; font-size: 0.68rem; font-weight: 700;
  color: var(--navy); margin-right: 4px;
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
.quote-cite .tier-a {
  display: inline-block; font-size: 0.68rem; font-weight: 700;
  color: var(--navy); margin-right: 4px;
}
.missing-note {
  margin: 10px 0 0; font-size: 0.95rem; color: var(--text-muted); line-height: 1.6;
}
.bucket-badge {
  font-size: 0.75rem; font-weight: 600; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap;
  background: color-mix(in srgb, var(--chip) 10%, var(--surface-1));
  color: var(--chip);
  border: 1px solid color-mix(in srgb, var(--chip) 26%, var(--hairline));
}
.term-metrics {
  display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 9px;
  font-size: 0.75rem; color: var(--text-muted); font-variant-numeric: tabular-nums;
}
.term-metrics b { color: var(--text-secondary); font-weight: 650; }
.term-metrics .m-strong b { color: var(--ink); }
.rec-bar {
  display: inline-block; width: 38px; height: 5px; border-radius: 3px;
  background: var(--gridline); vertical-align: 1px; margin-left: 4px;
  overflow: hidden;
}
.rec-bar i { display: block; height: 100%; background: var(--gold); }
.term-variants {
  margin-top: 7px; font-size: 0.75rem; color: var(--text-muted);
  letter-spacing: -0.01em;
}
/* 설명 블록 — 참고기사 위에 한 겹 더 그은 흐린 선 안쪽에 들어간다 */
.term-def {
  margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--gridline);
}
.term-def .def-one {
  margin: 0 0 8px; font-size: 1rem; line-height: 1.6;
  font-weight: 650; color: var(--ink); letter-spacing: -0.02em;
}
.term-def p.def-body {
  margin: 0 0 7px; font-size: 1rem; line-height: 1.72;
  color: var(--text-secondary); letter-spacing: -0.01em;
}
.term-def p.def-body:last-of-type { margin-bottom: 0; }
.term-def strong, .quote-ko strong { font-weight: 700; color: var(--ink); }
.term-def u, .quote-ko u {
  text-decoration: underline 1px;
  text-underline-offset: 2px;
  text-decoration-color: color-mix(in srgb, var(--ink) 55%, transparent);
}
.term-def .def-src {
  margin: 8px 0 0; font-size: 0.75rem; color: var(--text-muted);
}
.term-def .def-src::before { content: "근거 · "; }
.term-examples {
  margin-top: 11px; padding-top: 9px; border-top: 1px solid var(--hairline);
}
.term-examples .ex-label {
  font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em; margin: 0 0 5px;
}
.term-examples ol { margin: 0; padding-left: 0; list-style: none; }
.term-examples li {
  font-size: 0.95rem; line-height: 1.5; margin-bottom: 3px;
  display: flex; gap: 7px; align-items: baseline;
}
.term-examples .ex-date {
  font-variant-numeric: tabular-nums; font-size: 0.75rem; color: var(--text-muted);
  flex: 0 0 auto; min-width: 5.2em;
}
.term-examples a {
  color: var(--navy); text-decoration: underline;
  text-decoration-thickness: 1px; text-underline-offset: 2px;
}
.term-examples a:hover { color: var(--accent); }
.term-examples .ex-src { font-size: 0.75rem; color: var(--text-muted); }

details.legend {
  margin: 0 0 16px; font-size: 0.95rem; color: var(--text-secondary);
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 12px; padding: 10px 14px;
}
details.legend summary {
  cursor: pointer; font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em;
}
details.legend table { border-collapse: collapse; margin-top: 10px; width: 100%; }
details.legend td { padding: 4px 8px 4px 0; vertical-align: top; line-height: 1.5; }
details.legend td:first-child {
  white-space: nowrap; font-weight: 700; color: var(--ink); font-size: 0.75rem;
}
.empty-note {
  padding: 28px 4px; color: var(--text-muted); font-size: 1rem; display: none;
}
.prose { font-size: 1rem; line-height: 1.75; }
.prose h2 {
  font-size: 15px; margin: 26px 0 8px; letter-spacing: -0.02em;
  padding-bottom: 6px; border-bottom: 1px solid var(--gridline);
}
.prose h3 { font-size: 0.95rem; margin: 18px 0 6px; color: var(--ink-muted); }
.prose table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 0.95rem; }
.prose th, .prose td {
  border-bottom: 1px solid var(--gridline); padding: 6px 8px;
  text-align: left; vertical-align: top; line-height: 1.55;
}
.prose th { color: var(--text-muted); font-size: 0.75rem; font-weight: 700; }
.prose code {
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 5px; padding: 1px 5px; font-size: 0.88em;
}
.prose pre {
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 10px; padding: 12px 14px; overflow-x: auto; font-size: 0.82rem;
}
.prose pre code { background: none; border: 0; padding: 0; }
.prose ul { padding-left: 20px; }
.prose li { margin-bottom: 4px; }
@media (max-width: 620px) {
  .source-chips { margin-left: 0; width: 100%; }
  .bucket-badge { margin-left: 0; }
  .term-examples li { flex-wrap: wrap; }
}

/* 2026-10 카드 개편 — 인쇄 카드 구성(장·표제어·구분·대체어·용어 설명·관련 용어·기관별·출처) */
.bucket-head .ch-en { font-weight: 500; font-size: 0.8rem; margin-left: 4px; }
.bucket-head .ch-cat {
  float: right; font-size: 0.72rem; font-weight: 600; color: var(--chip);
}
.term-card { padding: 16px 18px 12px; scroll-margin-top: 52px; }
.term-card.flash { animation: flash 1.6s ease-out; }
@keyframes flash {
  0% { box-shadow: 0 0 0 3px color-mix(in srgb, var(--chip) 45%, transparent); }
  100% { box-shadow: 0 0 0 3px transparent; }
}
.card-top {
  display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;
  font-size: 0.75rem; color: var(--text-muted);
}
.card-top .term-n { color: var(--chip); font-weight: 700; text-decoration: none; min-width: 0; }
.card-top .term-n:hover { text-decoration: underline; }
.card-chapter { font-weight: 600; letter-spacing: -0.02em; }
.card-chapter .ch-en { font-weight: 400; }
h2.term-title {
  margin: 4px 0 8px; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline;
  font-size: inherit; font-weight: inherit;
}
h2.term-title .term-name { font-size: 1.2rem; }
dl.term-meta {
  display: flex; flex-wrap: wrap; gap: 4px 22px; margin: 0 0 10px;
  font-size: 0.88rem; line-height: 1.5;
}
dl.term-meta div { display: flex; gap: 8px; min-width: 0; }
dl.term-meta dt {
  font-size: 0.72rem; font-weight: 700; color: var(--chip); padding-top: 2px; flex: 0 0 auto;
}
dl.term-meta dd { margin: 0; color: var(--text-secondary); }
h3.sec {
  margin: 0 0 6px; font-size: 0.75rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--chip);
}
.term-explain, .term-fw, .term-refs {
  border-top: 1px solid var(--gridline); padding-top: 10px; margin-top: 10px;
}
.def-lead {
  margin: 0 0 6px; font-size: 1rem; line-height: 1.6; font-weight: 650;
  color: var(--ink); letter-spacing: -0.02em;
}
ul.def-points, .term-fw ul { margin: 0; padding-left: 1.1em; }
ul.def-points li, .term-fw li {
  font-size: 0.95rem; line-height: 1.68; color: var(--text-secondary);
  letter-spacing: -0.01em; margin-bottom: 3px;
}
.def-distinction {
  margin: 8px 0 0; padding: 8px 12px; background: var(--surface-2);
  border: 1px solid var(--gridline); border-radius: 8px;
  font-size: 0.92rem; line-height: 1.62; color: var(--text-secondary);
}
.term-related {
  margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline;
  font-size: 0.9rem;
}
.term-related .sec-inline {
  font-size: 0.75rem; font-weight: 700; color: var(--chip); margin-right: 2px;
}
.term-related a { color: var(--navy); text-decoration: none; }
.term-related a:hover { text-decoration: underline; color: var(--accent); }
.term-related span:not(.sec-inline) { color: var(--text-muted); }
.fw-row {
  display: grid; grid-template-columns: 7.5em 1fr; gap: 10px;
  padding: 7px 0; border-bottom: 1px dashed var(--gridline);
}
.fw-row:last-child { border-bottom: 0; }
.fw-org { font-size: 0.85rem; font-weight: 700; color: var(--ink); line-height: 1.4; }
.fw-org span { display: block; font-weight: 500; font-size: 0.75rem; color: var(--text-muted); }
a.ref-sup {
  font-size: 0.72rem; color: var(--text-muted); text-decoration: none;
  font-variant-numeric: tabular-nums;
}
a.ref-sup:hover { color: var(--accent); }
.term-refs ol { margin: 0; padding: 0; list-style: none; }
.term-refs li {
  display: flex; gap: 8px; font-size: 0.82rem; line-height: 1.55;
  color: var(--text-secondary); margin-bottom: 3px; scroll-margin-top: 60px;
}
.term-refs li:target { background: color-mix(in srgb, var(--gold) 18%, transparent); }
.ref-n {
  flex: 0 0 auto; min-width: 1.4em; height: 1.4em; border-radius: 50%;
  background: color-mix(in srgb, var(--chip) 14%, var(--surface-1)); color: var(--chip);
  font-size: 0.7rem; font-weight: 700; display: inline-flex; align-items: center;
  justify-content: center; margin-top: 1px;
}
details.term-more {
  margin-top: 10px; border-top: 1px solid var(--gridline); padding-top: 8px;
}
details.term-more summary {
  cursor: pointer; font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em;
}
details.term-more summary:hover { color: var(--ink); }
.term-commentary p {
  margin: 0 0 7px; font-size: 0.95rem; line-height: 1.72; color: var(--text-secondary);
}
.term-commentary strong { color: var(--ink); }
.ex-tag {
  font-size: 0.68rem; font-weight: 700; color: var(--navy);
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 0 4px; margin-left: 2px;
}
.term-examples a.ex-digest, a.lib-link {
  font-size: 0.75rem; color: var(--text-muted); text-decoration: underline;
  text-decoration-thickness: 1px; text-underline-offset: 2px; margin-left: 4px;
}
a.lib-link { margin-left: 0; }
.prose .muted { color: var(--text-muted); font-size: 0.85em; }
.prose td.num, .prose th.num { text-align: right; font-variant-numeric: tabular-nums; }
@media (max-width: 620px) {
  .fw-row { grid-template-columns: 1fr; gap: 2px; }
  .fw-org span { display: inline; margin-left: 6px; }
  .bucket-head .ch-cat { float: none; display: block; }
}

/* 용어 관계 — 맨 위 개념 지도와 카드 안 관계도 (relmap.py) */
.concept-maps {
  background: var(--surface-1); border: 1px solid var(--hairline); border-radius: 14px;
  padding: 14px 16px 10px; margin: 0 0 6px;
}
.map-head { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.map-head h2 { margin: 0; font-size: 0.95rem; letter-spacing: -0.02em; }
.map-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
.map-desc { margin: 6px 0 4px; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; }
.rel-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
svg.rel-map { display: block; width: 100%; min-width: 640px; height: auto; }
svg.rel-ego { display: block; width: 100%; max-width: 620px; min-width: 500px; height: auto; margin: 0 auto; }
svg .rel-n rect { transition: stroke-width .12s; }
svg a.rel-n:hover rect { stroke-width: 2.6; }
svg a.rel-n:hover text { text-decoration: underline; }
svg a.rel-n:focus-visible rect { stroke-width: 3; }
.rel-legend-wrap {
  display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px;
  border-top: 1px solid var(--gridline); margin-top: 6px; padding-top: 6px;
}
svg.rel-legend { width: 560px; max-width: 100%; height: auto; }
.map-hint { font-size: 0.72rem; color: var(--text-muted); }
.term-rel { border-top: 1px solid var(--gridline); padding-top: 10px; margin-top: 10px; }
"""


def page(title, current, body, *, head_count=None, extra_js=""):
    chrome = ui.page_chrome(current, {"docs": []}, head_count=head_count)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{chrome['nav_css']}{GLOSSARY_CSS}</style>
</head>
<body>
<div class="viz-root">
{chrome['shell']}
<main class="wrap">
{body}
</main>
{ui.footer_html()}
</div>
{extra_js}
</body>
</html>
"""


LIBRARY_DOC_URL = ui.LIBRARY_URL + "#{}"
DIGEST_DAY_URL = ui.DIGEST_URL + "daily/{}.html"
SOURCE_LABEL = {"kit": "번역 용어 정본", "kit-variant": "정본 변형", "public": "이전 표기",
                "observed": "코퍼스 관찰", "card": "인쇄 카드", "editor": "편집"}


def nospace(s):
    return "".join((s or "").split())


def pages_label(d):
    page_s = d.get("pages_label") or ""
    if not page_s:
        page, page_end = d.get("pdf_page_start"), d.get("pdf_page_end")
        if page and page_end and page != page_end:
            page_s = f"p.{page}–{page_end}"
        elif page:
            page_s = f"p.{page}"
    return page_s


def library_link(lib_id, label="라이브러리에서 보기"):
    if not lib_id:
        return ""
    return (f' · <a class="lib-link" href="{html.escape(LIBRARY_DOC_URL.format(lib_id))}" '
            f'target="_blank" rel="noopener">{label}</a>')


def pdf_quotes_html(defs):
    blocks = []
    for d in defs:
        page_s = pages_label(d)
        kind = "정의섹션" if d.get("source_kind") == "definition_section" else "본문"
        ko = ""
        if d.get("quote_ko"):
            ko = (f'<p class="quote-ko"><span class="ko-label">번역</span>'
                  f'{ui.prose_with_emphasis(d["quote_ko"])}</p>')
        title = d.get("title") or d.get("short") or ""
        blocks.append(
            f'<div class="quote-block">{ko}'
            f'<p class="quote-text">{html.escape(d.get("quote") or "")}</p>'
            f'<p class="quote-cite"><span class="cite-label">출처</span> {html.escape(title)}'
            f'{(" · " + html.escape(page_s)) if page_s else ""}'
            f' · {html.escape(d.get("language") or "")} · {kind}'
            f'{library_link(d.get("library_id"))}</p></div>'
        )
    return "".join(blocks)


def examples_html(examples):
    if not examples:
        return ""
    lis = []
    for x in examples:
        dd = x.get("digest_date")
        day = (f' <a class="ex-digest" href="{html.escape(DIGEST_DAY_URL.format(dd))}" '
               f'target="_blank" rel="noopener">다이제스트 {html.escape(dd)}</a>') if dd else ""
        tag = ' <span class="ex-tag">연구</span>' if x.get("research") else ""
        lis.append(
            '<li><span class="ex-date">{d}</span><span><a href="{u}" target="_blank" rel="noopener">{t}</a>'
            ' <span class="ex-src">{s}</span>{tag}{day}</span></li>'.format(
                d=html.escape((x.get("date") or "")[:10]), u=html.escape(x.get("url") or ""),
                t=html.escape(x.get("title") or ""),
                s=html.escape((x.get("source") or "").split("·")[-1].strip()[:22]), tag=tag, day=day))
    return ('<div class="term-examples"><p class="ex-label">참고 기사·연구</p>'
            f'<ol>{"".join(lis)}</ol></div>')


def metrics_html(e):
    m = e["metrics"]
    out = []
    if e["source"] in ("digest", "both"):
        rec_pct = round((m.get("recency") or 0) * 100)
        out.append(
            f'<span title="동향 코퍼스 문서 수">동향 문서 <b>{m.get("df", 0)}</b></span>'
            f'<span title="등장한 서로 다른 달 수">기간 <b>{m.get("months", 0)}</b>개월</span>'
            f'<span title="최근 12개월 비중">최근 <b>{rec_pct}%</b>'
            f'<span class="rec-bar"><i style="width:{rec_pct}%"></i></span></span>'
            f'<span title="원문이 괄호로 뜻을 풀어 쓴 문서 수">병기 <b>{m.get("gloss", 0)}</b></span>')
    if e["source"] in ("pdf", "both"):
        out.append(
            f'<span title="PDF 코퍼스 문서 수">PDF 문서 <b>{m.get("pdf_df", 0)}</b></span>'
            f'<span title="정의 섹션 등장 문서 수">정의섹션 <b>{m.get("pdf_gloss_df", 0)}</b></span>')
    return f'<div class="term-metrics">{"".join(out)}</div>' if out else ""


def ref_sup(cid, ns):
    return "".join(f' <a class="ref-sup" href="#{html.escape(cid)}-ref-{n}">[{n}]</a>' for n in ns or [])


REL_CTX = {"nodes": {}, "color": {}}


def rel_section(e):
    svg = relmap.ego_svg(e, REL_CTX["nodes"], lambda i: REL_CTX["color"].get(i, "var(--navy)"))
    if not svg:
        return ""
    return f'<section class="term-rel"><h3 class="sec">용어 관계</h3><div class="rel-scroll">{svg}</div></section>'


def card_html(e):
    cid = e["id"]
    d = e.get("definition") or {}
    alts = e.get("alternatives") or []

    meta = [f'<div><dt>구분</dt><dd>{html.escape(e["category_label"])}</dd></div>']
    if alts:
        alt_s = " · ".join(
            f'<span title="{html.escape(SOURCE_LABEL.get(a.get("source"), ""))}">{html.escape(a["text"])}</span>'
            for a in alts)
        meta.append(f'<div><dt>대체어</dt><dd>{alt_s}</dd></div>')

    explain = []
    if d.get("lead"):
        explain.append(f'<p class="def-lead">{ui.prose_with_emphasis(d["lead"])}</p>')
    if d.get("points"):
        explain.append('<ul class="def-points">' + "".join(
            f"<li>{ui.prose_with_emphasis(p)}</li>" for p in d["points"]) + "</ul>")
    dist = d.get("distinction")
    if dist and dist.get("text"):
        explain.append(f'<p class="def-distinction">{ui.prose_with_emphasis(dist["text"])}</p>')

    related = ""
    if e.get("related"):
        tags = []
        for r in e["related"]:
            if r.get("id"):
                tags.append(f'<a href="#{html.escape(r["id"])}">#{html.escape(nospace(r["head"]))}</a>')
            else:
                tags.append(f'<span>#{html.escape(nospace(r["label"]))}</span>')
        related = f'<p class="term-related"><span class="sec-inline">관련 용어</span>{"".join(tags)}</p>'

    fw = ""
    if e.get("frameworks"):
        rows = []
        for f in e["frameworks"]:
            pts = "".join(
                f'<li>{ui.prose_with_emphasis(p["text"] if isinstance(p, dict) else p)}'
                f'{ref_sup(cid, p.get("refs") if isinstance(p, dict) else None)}</li>'
                for p in f.get("points") or [])
            rows.append(
                f'<div class="fw-row"><div class="fw-org">{html.escape(f.get("org", ""))}'
                f'{("<span>" + html.escape(str(f["sub"])) + "</span>") if f.get("sub") else ""}</div>'
                f'<ul>{pts}</ul></div>')
        fw = f'<section class="term-fw"><h3 class="sec">주요 기관·문서별 개념 및 적용</h3>{"".join(rows)}</section>'

    refs = ""
    if e.get("refs"):
        lis = "".join(
            f'<li id="{html.escape(cid)}-ref-{r.get("n")}"><span class="ref-n">{r.get("n")}</span>'
            f'<span>{html.escape(r.get("text", ""))}'
            f'{(" · " + html.escape(r["evidence"]["pages"])) if (r.get("evidence") or {}).get("pages") and r["evidence"]["pages"] not in r.get("text", "") else ""}'
            f'{(" · <a href=" + chr(34) + html.escape(r["url"]) + chr(34) + " target=_blank rel=noopener>원문</a>") if r.get("url") else ""}'
            f'{library_link(r.get("library_id"))}</span></li>'
            for r in e["refs"])
        refs = f'<section class="term-refs"><h3 class="sec">출처</h3><ol>{lis}</ol></section>'

    more = []
    if e.get("commentary"):
        more.append('<p class="section-label">해설</p><div class="term-commentary">' + "".join(
            f'<p>{ui.prose_with_emphasis(p)}</p>' for p in e["commentary"]) + "</div>")
    if e.get("pdf_definitions"):
        more.append('<p class="section-label">PDF 원문 인용</p>' + pdf_quotes_html(e["pdf_definitions"]))
    more.append(examples_html(e.get("examples")))
    if e.get("variants"):
        more.append("".join(
            f'<div class="term-variants">{k} 표기 · {html.escape(v)}</div>' for k, v in e["variants"]))
    more.append(metrics_html(e))
    more_s = "".join(x for x in more if x)
    n_more = len(e.get("pdf_definitions") or []) + len(e.get("examples") or [])
    more_label = []
    if e.get("commentary"):
        more_label.append("해설")
    if e.get("pdf_definitions"):
        more_label.append(f"원문 인용 {len(e['pdf_definitions'])}")
    if e.get("examples"):
        more_label.append(f"참고 기사 {len(e['examples'])}")
    more_html = (f'<details class="term-more"><summary>{" · ".join(more_label) or "지표"}</summary>{more_s}</details>'
                 if more_s.strip() else "")

    q_bits = [e["head"], e["en"], e["chapter_label"], e["category_label"]]
    q_bits += [a["text"] for a in alts]
    q_bits += [d.get("lead") or ""] + list(d.get("points") or []) + [(dist or {}).get("text") or ""]
    q_bits += [r.get("head") or r.get("label") or "" for r in e.get("related") or []]
    q_bits += list(e.get("commentary") or [])
    q_bits += [f.get("org", "") for f in e.get("frameworks") or []]
    q_bits += [x.get("title") or "" for x in e.get("examples") or []]
    for dd in e.get("pdf_definitions") or []:
        q_bits += [dd.get("quote") or "", dd.get("quote_ko") or ""]

    return (
        f'<article class="term-card" id="{html.escape(cid)}" data-cat="{e["category"]}" '
        f'data-ch="{e["chapter"]}" data-n="{e["n"]}" data-head="{html.escape(e["head"])}" '
        f'data-q="{html.escape(" ".join(q_bits).lower())}" '
        f'data-qn="{html.escape(nospace(" ".join([e["head"], e["en"]] + [a["text"] for a in alts])).lower())}" style="--chip:{html.escape(e["color"])}">'
        f'<div class="card-top"><a class="term-n" href="#{html.escape(cid)}" title="이 용어 링크">{e["n"]:03d}</a>'
        f'<span class="card-chapter">{e["chapter"]}. {html.escape(e["chapter_label"])}'
        f' <span class="ch-en">({html.escape(e["chapter_en"])})</span></span></div>'
        f'<h2 class="term-title"><span class="term-name">{html.escape(e["head"])}</span>'
        f'<span class="term-en">{html.escape(e["en"])}</span></h2>'
        f'<dl class="term-meta">{"".join(meta)}</dl>'
        f'<section class="term-explain"><h3 class="sec">용어 설명</h3>{"".join(explain)}</section>'
        f"{rel_section(e)}{related}{fw}{refs}{more_html}"
        f"</article>"
    )


LEGEND = """<details class="legend">
<summary>카드 읽는 법</summary>
<table>
<tr><td>표제어</td><td>번역 용어 정본(ai-safety-translation-kit)의 번역어를 기본으로 한다. 일상어라서 그 자체로는 개념어로 읽기 어려운 말에는 AI를 붙였다(AI 안전·AI 위험·AI 사고 보고).</td></tr>
<tr><td>대체어</td><td>함께 쓰이는 다른 표기. 마우스를 올리면 출처(정본 변형·이전 표기·편집)가 보인다.</td></tr>
<tr><td>용어 설명</td><td>굵은 한 줄이 정의, 아래 항목이 AI 안전 관점의 부연, 회색 상자가 헷갈리기 쉬운 용어와의 구별이다.</td></tr>
<tr><td>기관·문서별</td><td>국제기구·표준·법령이 그 개념을 어떻게 정의하고 적용하는지. 번호는 출처 목록을 가리킨다.</td></tr>
<tr><td>용어 관계</td><td>가운데가 이 용어. 위는 상위어, 아래는 하위어, 왼쪽은 먼저 알 개념·앞 단계, 오른쪽은 다음 단계·혼동 주의 용어다. 상자를 누르면 그 카드로 간다.</td></tr>
<tr><td>펼치기</td><td>해설, PDF 원문 인용(쪽수), 다이제스트 참고 기사, 코퍼스 지표.</td></tr>
</table>
</details>"""


def concept_maps_html(data):
    path = os.path.join(config.DATA, "concept_maps.json")
    if not os.path.exists(path):
        return ""
    maps = json.load(open(path, encoding="utf-8"))["maps"]
    edges = [tuple(x) for x in data.get("relations") or []]
    color = lambda i: REL_CTX["color"].get(i, "var(--navy)")
    tabs, panels = [], []
    for i, m in enumerate(maps):
        act = " active" if i == 0 else ""
        tabs.append(f'<button class="filter-chip map-tab{act}" data-map="{m["id"]}">{html.escape(m["title"])}</button>')
        panels.append(
            f'<div class="map-panel" data-map="{m["id"]}"{"" if i == 0 else " hidden"}>'
            f'<p class="map-desc">{html.escape(m.get("desc", ""))}</p>'
            f'<div class="rel-scroll">{relmap.concept_map_svg(m, REL_CTX["nodes"], edges, color)}</div></div>')
    tabbar = f'<div class="map-tabs">{"".join(tabs)}</div>' if len(maps) > 1 else ""
    return (f'<section class="concept-maps" aria-label="개념 지도">'
            f'<div class="map-head"><h2>개념 지도</h2>{tabbar}</div>{"".join(panels)}'
            f'<div class="rel-legend-wrap">{relmap.LEGEND_SVG}<span class="map-hint">상자를 누르면 그 용어 카드로 갑니다.</span></div>'
            f'</section>')


def index_page(data):
    ents = data["entries"]
    cats = data["categories"]
    chs = data["chapters"]
    cat_color = {c["code"]: c["color"] for c in cats}
    cat_chips = "".join(
        f'<button class="filter-chip" data-cat="{c["code"]}" style="--chip:{c["color"]}">'
        f'{html.escape(c["label"])} <span class="n">{c["n"]}</span></button>'
        for c in cats if c["n"])
    ch_chips = "".join(
        f'<button class="filter-chip" data-ch="{c["no"]}" data-chcat="{c["category"]}" '
        f'style="--chip:{cat_color[c["category"]]}">{c["no"]}. {html.escape(c["label"])} '
        f'<span class="n">{c["n"]}</span></button>'
        for c in chs if c["n"])
    sorts = [("ch", "장순"), ("ko", "가나다")]
    sort_chips = "".join(
        f'<button class="filter-chip{" active" if k == "ch" else ""}" data-sort="{k}">{html.escape(lb)}</button>'
        for k, lb in sorts)
    ch_meta = {c["no"]: {"label": c["label"], "en": c["en"], "cat": c["category"],
                         "color": cat_color[c["category"]]} for c in chs}
    cat_label = {c["code"]: c["label"] for c in cats}
    legacy_path = os.path.join(config.DATA, "legacy_anchors.json")
    legacy = json.load(open(legacy_path, encoding="utf-8"))["map"] if os.path.exists(legacy_path) else {}
    REL_CTX["nodes"] = {e["id"]: {"id": e["id"], "head": e["head"], "en": e["en"]} for e in ents}
    REL_CTX["color"] = {e["id"]: e["color"] for e in ents}
    cards = "".join(card_html(e) for e in ents)
    maps_html = concept_maps_html(data)
    c = data.get("corpus") or {}
    corpus_note = html.escape("동향 코퍼스 {:,}건 기준".format(c["docs"])) if c.get("docs") else ""
    body = f"""{maps_html}
{ui.omnibox_html()}
{LEGEND}
<div id="listControls">
  <div class="filter-toolbar">
    <span class="filter-label">구분</span>
    <button class="filter-chip active" data-cat="">전체 <span class="n">{len(ents)}</span></button>
    {cat_chips}
  </div>
  <div class="filter-toolbar">
    <span class="filter-label">장</span>
    <button class="filter-chip active" data-ch="">전체</button>
    {ch_chips}
  </div>
  <div class="filter-toolbar">
    <span class="filter-label">정렬</span>
    {sort_chips}
  </div>
</div>
<p class="result-line" id="resultLine" data-corpus="{corpus_note}">{len(ents)}개 표제어</p>
<div id="termList">{cards}</div>
<p class="empty-note" id="emptyNote">검색 결과가 없습니다.</p>
"""
    js = """<script>
(function () {
  var CH = __CH__, CAT = __CAT__, LEGACY = __LEGACY__;
  var list = document.getElementById('termList');
  var cards = Array.prototype.slice.call(list.querySelectorAll('.term-card'));
  var box = document.getElementById('omniBox');
  var line = document.getElementById('resultLine');
  var note = document.getElementById('emptyNote');
  var panel = document.getElementById('omniResults');
  if (panel) panel.remove();
  var state = { cat: '', ch: '', sort: 'ch', q: '' };
  var total = cards.length;
  var params = new URLSearchParams(location.search);
  state.q = params.get('q') || '';
  state.cat = CAT[params.get('cat')] ? params.get('cat') : '';
  state.ch = CH[params.get('ch')] ? params.get('ch') : '';
  if (state.ch) state.cat = CH[state.ch].cat;
  if (box && state.q) box.value = state.q;

  function num(c, k) { return parseFloat(c.dataset[k]) || 0; }
  function syncUrl() {
    var p = new URLSearchParams();
    if (state.q.trim()) p.set('q', state.q.trim());
    if (state.ch) p.set('ch', state.ch); else if (state.cat) p.set('cat', state.cat);
    var s = p.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : '') + location.hash);
  }
  function syncChips() {
    document.querySelectorAll('button[data-cat]').forEach(function (o) {
      o.classList.toggle('active', o.dataset.cat === state.cat);
    });
    document.querySelectorAll('button[data-ch]').forEach(function (o) {
      o.classList.toggle('active', o.dataset.ch === state.ch);
      o.hidden = !!(o.dataset.chcat && state.cat && o.dataset.chcat !== state.cat);
    });
    document.querySelectorAll('button[data-sort]').forEach(function (o) {
      o.classList.toggle('active', o.dataset.sort === state.sort);
    });
  }
  function apply() {
    var q = state.q.trim().toLowerCase();
    var qn = q.replace(/\\s+/g, '');  // 붙여 쓴 표기로도 표제어·대체어를 찾는다
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!state.cat || c.dataset.cat === state.cat) &&
               (!state.ch || c.dataset.ch === state.ch) &&
               (!q || c.dataset.q.indexOf(q) !== -1 || c.dataset.qn.indexOf(qn) !== -1);
      c.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });
    var vis = cards.filter(function (c) { return !c.classList.contains('hidden'); });
    if (state.sort === 'ch') {
      vis.sort(function (a, b) { return num(a, 'n') - num(b, 'n'); });
    } else {
      vis.sort(function (a, b) { return a.dataset.head.localeCompare(b.dataset.head, 'ko'); });
    }
    list.querySelectorAll('.bucket-head').forEach(function (h) { h.remove(); });
    var frag = document.createDocumentFragment();
    var last = null;
    vis.forEach(function (c) {
      if (state.sort === 'ch' && c.dataset.ch !== last) {
        last = c.dataset.ch;
        var m = CH[last];
        var h = document.createElement('div');
        h.className = 'bucket-head';
        h.style.setProperty('--chip', m.color);
        h.innerHTML = '<span class="bk">' + last + '.</span> ' + m.label +
          ' <span class="ch-en">' + m.en + '</span><span class="ch-cat">' + CAT[m.cat] + '</span>';
        frag.appendChild(h);
      }
      frag.appendChild(c);
    });
    list.appendChild(frag);
    note.style.display = shown ? 'none' : 'block';
    var corpus = line.dataset.corpus ? ' · ' + line.dataset.corpus : '';
    line.textContent = (shown === total ? total + '개 표제어' : shown + ' / ' + total + '개 표시') + corpus;
    syncChips();
    syncUrl();
  }
  function reveal(id) {
    var el = document.getElementById(id);
    if (!el || !el.classList.contains('term-card')) return;
    if (el.classList.contains('hidden')) {
      state.cat = ''; state.ch = ''; state.q = ''; if (box) box.value = ''; apply();
    }
    el.scrollIntoView({ block: 'start' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  }
  function onHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    if (!h) return;
    var m = /^t(\\d+)$/.exec(h);
    if (m && LEGACY[m[1]]) { history.replaceState(null, '', '#' + LEGACY[m[1]]); h = LEGACY[m[1]]; }
    var card = document.getElementById(h);
    if (!card) { var r = /^(.*)-ref-\\d+$/.exec(h); if (r) card = document.getElementById(r[1]); }
    if (card) reveal(card.id);
    var target = document.getElementById(h);
    if (target && target !== card) target.scrollIntoView({ block: 'center' });
  }
  document.querySelectorAll('button[data-cat]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.cat = b.dataset.cat;
      if (state.ch && CH[state.ch].cat !== state.cat) state.ch = '';
      apply();
    });
  });
  document.querySelectorAll('button[data-ch]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.ch = b.dataset.ch;
      if (state.ch) state.cat = CH[state.ch].cat;
      apply();
    });
  });
  document.querySelectorAll('button[data-sort]').forEach(function (b) {
    b.addEventListener('click', function () { state.sort = b.dataset.sort; apply(); });
  });
  if (box) {
    box.addEventListener('input', function () { state.q = box.value; apply(); });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === '/' && ev.target.tagName !== 'INPUT') { ev.preventDefault(); box.focus(); }
      if (ev.key === 'Escape') { box.value = ''; state.q = ''; apply(); box.blur(); }
    });
  }
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href^="http"]');
    if (a) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
  }, true);
  document.querySelectorAll('button.map-tab').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('button.map-tab').forEach(function (o) { o.classList.toggle('active', o === b); });
      document.querySelectorAll('.map-panel').forEach(function (pn) { pn.hidden = pn.dataset.map !== b.dataset.map; });
    });
  });
  window.addEventListener('hashchange', onHash);
  if ('scrollRestoration' in history && location.hash) history.scrollRestoration = 'manual';
  apply();
  onHash();
  // 카드 재배치·웹폰트 적용 뒤에 위치가 밀리므로 load 뒤 한 번 더 맞춘다
  window.addEventListener('load', function () { setTimeout(onHash, 0); });
})();
</script>"""
    js = (js.replace("__CH__", ui.safe_json(ch_meta))
            .replace("__CAT__", ui.safe_json(cat_label))
            .replace("__LEGACY__", ui.safe_json(legacy)))
    return page("AI 안전 용어집", "index.html", body, head_count=len(ents), extra_js=js)


def about_page(data):
    c = data.get("corpus") or {}
    cnt = (data.get("meta") or {}).get("counts") or {}
    docs = c.get("docs", 0)
    cat_label = {x["code"]: x["label"] for x in data["categories"]}
    ch_rows = "".join(
        f'<tr><td>{html.escape(cat_label[x["category"]])}</td><td>{x["no"]}. {html.escape(x["label"])}'
        f' <span class="muted">{html.escape(x["en"])}</span></td><td class="num">{x["n"]}</td></tr>'
        for x in data["chapters"])
    excl_path = os.path.join(config.DATA, "excluded.json")
    excl = json.load(open(excl_path, encoding="utf-8")) if os.path.exists(excl_path) else []
    excl_s = ", ".join(html.escape(x["head"]) for x in excl)
    pdf_docs = sorted({(d.get("short") or d.get("title") or "") for e in data["entries"]
                       for d in e.get("pdf_definitions") or []} - {""})
    body = f"""<div class="prose">
<p>AI 안전 연구·정책에서 자주 쓰는 용어를 <b>AI 안전 관점</b>에서 풀어 쓴 용어집입니다.
현재 표제어 <b>{len(data['entries'])}개</b>를 4개 구분, 11개 장으로 묶었습니다.
인쇄용 용어 카드(50선)도 이 온라인판에서 골라 만듭니다.</p>

<h2>구성 — 구분과 장</h2>
<p>기술이 무엇인지에서 시작해 무엇이 잘못될 수 있는지, 어떻게 확인하고 막는지,
누가 어떤 규칙으로 다스리는지의 순서로 장을 놓았습니다. 용어는 장 하나에만 속하고,
장을 넘는 연결은 카드의 <b>관련 용어</b>로 잇습니다.</p>
<table><tr><th>구분</th><th>장</th><th class="num">표제어</th></tr>{ch_rows}</table>

<h2>표제어 원칙</h2>
<ul>
<li><b>번역어는 번역 용어 정본(ai-safety-translation-kit)을 따릅니다.</b> 연구소 번역 작업에 쓰는
승인 용어집입니다. 정본에 없는 용어는 편집 판단으로 정하고, 정본에 반영할 후보로 올립니다.</li>
<li><b>띄어쓰기는 정본에 맞춰 통일했습니다</b>(해석 가능성, 허위 정보, 사이버 보안, 오픈 웨이트 모델).
붙여 쓴 표기로 검색해도 찾을 수 있습니다.</li>
<li><b>일상어 표제어에는 AI를 붙였습니다.</b> 업계에서는 그냥 '안전', '위험', '사고 보고'로 쓰더라도,
일상어 그대로는 개념어로 읽기 어려워서입니다(AI 안전, AI 위험, AI 피해, AI 사고, AI 사고 보고).
일반 위험관리·보안 분야에서 빌려 온 절차 용어(위험 평가, 위험 허용도, 위협 모델링)에는 붙이지 않았습니다.</li>
<li><b>다른 표기는 대체어로 함께 적습니다.</b> 이전 판의 표기, 정본의 변형 표기, 현장에서 쓰는 음차어 등입니다.</li>
</ul>

<h2>카드 구성</h2>
<p>각 카드는 인쇄용 카드와 같은 순서입니다 — 장 · 표제어/영문 · 구분 · 대체어 · 용어 설명
(굵은 한 줄 정의, 부연, 혼동 용어와의 구별) · 관련 용어 · 주요 기관·문서별 개념 및 적용 · 출처.
펼치기 아래에는 온라인판에만 있는 해설, PDF 원문 인용, 참고 기사, 코퍼스 지표가 있습니다.</p>
<p>용어 설명은 이 용어집을 위해 쓴 글이며 인용문이 아닙니다. 기관·문서별 항목은 원문과
쪽수를 확인한 것만 실었고(현재 {cnt.get('with_frameworks', 0)}개 표제어), 확인하지 못한 수치나 조문 번호는 쓰지 않았습니다.
인용이 필요한 자리에서는 출처의 원 문헌을 확인해 주세요.</p>

<h2>개념 지도와 용어 관계</h2>
<p>용어 사이의 관계를 네 가지로 나눠 기록했습니다 — <b>상위·하위</b>(포함: AI 사고 ⊃ 중대 AI 사고),
<b>이어짐</b>(인과·단계: AI 위험원 → AI 사고), <b>먼저 알 개념</b>(정의에 다른 개념이 필요한 경우:
기만·오정렬 → 계략적 행동), <b>혼동 주의</b>(허위 정보 ↔ 오정보). 맨 위 개념 지도는 이 관계로
주제별 핵심 용어를 한 장씩 배치한 것이고, 카드마다 있는 <b>용어 관계</b> 그림은 그 용어 주변만 보여 줍니다.
관계는 현재 {data.get('meta', {}).get('counts', {}).get('relations', 0)}개입니다.</p>

<h2>근거 자료와 다른 사이트</h2>
<table>
<tr><th>자료</th><th>용어집에서 쓰는 곳</th></tr>
<tr><td><a href="{ui.DIGEST_URL}" target="_blank" rel="noopener">AI 안전 다이제스트</a></td>
<td>매일 모으는 뉴스·정책 동향. 표제어 후보 추출과 <b>참고 기사</b>의 출처입니다
(빌드 시점 {docs:,}건, {html.escape(str(c.get('from', '')))} ~ {html.escape(str(c.get('to', '')))}).
기사마다 원문 링크와 함께 그 기사가 실린 다이제스트 날짜 페이지를 잇습니다.</td></tr>
<tr><td><a href="{ui.RESEARCH_URL}" target="_blank" rel="noopener">AI 안전 연구</a></td>
<td>논문·연구 보고서 카탈로그. 참고 기사 가운데 <span class="ex-tag">연구</span> 표시가 붙은 항목이 연구 문헌입니다.</td></tr>
<tr><td>PDF 근거 색인</td>
<td>국제 보고서·법령·가이드라인 PDF를 쪽 단위로 색인한 연구소 내부 자료(PDF Evidence Desk)입니다.
<b>PDF 원문 인용</b>과 쪽수가 여기서 옵니다. 현재 문서 {len(pdf_docs)}종: {html.escape(', '.join(pdf_docs))}.</td></tr>
<tr><td><a href="{ui.LIBRARY_URL}" target="_blank" rel="noopener">AI 안전 라이브러리</a></td>
<td>정책·보고서 문서 목록. 인용 문서가 라이브러리에 있으면 출처 옆에 <b>라이브러리에서 보기</b>를 붙입니다.</td></tr>
</table>
<p>용어마다 고정 주소가 있습니다. 카드 왼쪽 위 번호를 누르면 그 용어의 주소가 됩니다
(예: <code>#incident-reporting</code>). 검색어와 장도 주소로 넘길 수 있습니다
(<code>?q=탈옥</code>, <code>?ch=07</code>).</p>

<h2>표제어 후보를 어떻게 모았나</h2>
<p>후보는 두 갈래로 기계적으로 모은 뒤 사람이 골랐습니다. 동향 코퍼스에서는 제목·요약의
한글·영문 n-gram을 긁어 분류 쿼터를 두고 100개를 골랐고, PDF 색인에서는 정의 섹션과 본문
빈도로 100개를 골랐습니다. 영문 표기로 합치면 173개였습니다. 2026년 10월 개편에서 중복을 합치고
AI 안전 관점의 설명이 어려운 일반 용어 {len(excl)}개({excl_s})를 뺐으며, 장마다 빠진 핵심 개념을 더했습니다.</p>
<p>후보를 고를 때 가장 쓸모 있었던 지표는 <b>병기율</b>입니다. 원문이 <code>표제어(뜻풀이)</code>처럼
괄호로 풀어 쓴 비율로, 필자가 "설명이 필요하다"고 판단한 흔적입니다. 이 지표로 사고 사슬(CoT),
보정, LLM 심판, 작업 시간 지평을 찾았습니다. 반대로 동시출현 그래프의 중심성(degree, 토픽 엔트로피,
PMI 가중 PageRank)은 '문제', '가능성' 같은 일반어만 끌어올렸습니다 — 코퍼스 전체가 이미 AI 안전
문서라서 그래프 중심성이 개념 위계가 아니라 상투적 연결어를 찾아낸 것입니다.</p>

<h2>알려진 한계</h2>
<ul>
<li><b>용어 설명은 편집 초안이 섞여 있습니다.</b> 검토를 거친 카드부터 차례로 보강합니다.
오류를 보시면 아래 메일로 알려 주세요.</li>
<li><b>참고 기사에 잡음이 있습니다.</b> 표기로만 찾아서, 광의어(예: 감사)는 다른 맥락의 기사가 걸릴 수 있습니다.</li>
<li><b>고유명사는 표제어에서 뺐습니다</b>(EU AI Act, NIST AI RMF, AISI 등).</li>
</ul>

<h2>소스</h2>
<p><a href="https://github.com/songkyungho/ai-safety-glossary" target="_blank"
rel="noopener">github.com/songkyungho/ai-safety-glossary</a></p>
</div>"""
    return page("소개 · AI 안전 용어집", "about.html", body)


def main():
    path = os.path.join(config.DATA, "glossary_site.json")
    if not os.path.exists(path):
        sys.exit("사이트 JSON이 없다: %s\n  python3 scripts/apply_editorial.py 를 먼저 실행하라." % path)
    data = json.load(open(path, encoding="utf-8"))
    os.makedirs(config.DOCS, exist_ok=True)
    for name, fn in (("index.html", index_page), ("about.html", about_page)):
        p = os.path.join(config.DOCS, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn(data))
        print("-> %s (%.1f KB)" % (p, os.path.getsize(p) / 1024))
    # 옛 PDF판 경로는 통합본으로 안내
    pdf_dir = os.path.join(config.DOCS, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    redirect = """<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=../index.html">
<link rel="canonical" href="../index.html">
<title>AI 안전 용어집</title>
</head><body>
<p><a href="../index.html">AI 안전 용어집</a>으로 이동합니다.</p>
</body></html>
"""
    for name in ("index.html", "about.html"):
        with open(os.path.join(pdf_dir, name), "w", encoding="utf-8") as f:
            f.write(redirect)
    with open(os.path.join(config.DOCS, ".nojekyll"), "w") as f:
        f.write("")
    stamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    print("빌드 %s · 표제어 %d" % (stamp, len(data["entries"])))


if __name__ == "__main__":
    main()
