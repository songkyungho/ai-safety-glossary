#!/usr/bin/env python3
"""정적 사이트 생성 — docs/index.html · docs/about.html.

페이지 틀(지면 토큰·전역 메뉴·머리띠·바닥글)은 ai-safety-common의 chrome에서 온다.
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
from aisafety_common import chrome, favicon, series  # noqa: E402 — ui_common이 ai-safety-common 경로를 잡아 준다
import relmap  # noqa: E402

KST = timezone(timedelta(hours=9))

GLOSSARY_CSS = """
/* 지면 토큰·전역 메뉴·머리띠·바닥글은 chrome(ai-safety-common) — 여기는 용어집만의 규칙 */
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
.term-examples .ex-label a { color: var(--navy); text-decoration: underline; text-underline-offset: 2px; }

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
  /* 연구 사이트 지도와 같은 넓은 배치 — 본문 폭을 넘어 화면 가운데에 */
  width: min(1220px, calc(100vw - 32px)); position: relative; left: 50%; transform: translateX(-50%);
  background: var(--surface-1); border: 1px solid var(--hairline); border-radius: 14px;
  padding: 14px 16px 10px; margin: 0 0 6px;
}
.map-head { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.map-head h2 { margin: 0; font-size: 0.95rem; letter-spacing: -0.02em; }
.map-head .map-hint { font-size: 0.75rem; color: var(--text-muted); }
.map-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
button.filter-chip .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--chip, var(--navy)); display: inline-block;
}
.map-desc { margin: 6px 0 4px; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; }
.rel-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
svg.rel-map { display: block; width: 100%; min-width: 640px; height: auto; }
svg.rel-ego { display: block; width: 100%; max-width: 620px; min-width: 500px; height: auto; margin: 0 auto; }
.rel-list { margin: 4px 0; font-size: 0.86rem; line-height: 1.7; color: var(--text-secondary); }
.rel-list b { font-weight: 600; color: var(--text-muted); margin-right: 2px; }
.rel-list a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--gridline); }
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

/* 2026-10 카드 디자인 v2 — 인쇄 카드 장치(번호 알약·장 띠·리본·라벨 알약·아이콘·기관별 색) */
.term-card {
  position: relative; padding: 0 0 12px; overflow: visible;
  border-left: 4px solid var(--ch, var(--chip));
}
.card-band {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  padding: 10px 150px 8px 16px;
  background: color-mix(in srgb, var(--ch) 7%, var(--surface-1));
  border-bottom: 1px solid color-mix(in srgb, var(--ch) 18%, var(--hairline));
  border-radius: 12px 12px 0 0;
}
.card-band .term-n {
  background: var(--navy); color: var(--on-navy); font-weight: 700; font-size: 0.78rem;
  padding: 2px 10px; border-radius: 6px; text-decoration: none; letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.card-band .term-n:hover { background: var(--accent); }
.card-band .card-chapter { font-size: 0.78rem; font-weight: 650; color: var(--ch); letter-spacing: -0.02em; }
.card-band .ch-en { font-weight: 400; color: var(--text-muted); }
.ribbon {
  position: absolute; top: -4px; right: 18px; z-index: 1;
  background: var(--chip); color: #fff; font-size: 0.72rem; font-weight: 700;
  letter-spacing: -0.01em; padding: 6px 12px 12px;
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% calc(100% - 6px), 0 100%);
  box-shadow: 0 1px 0 rgba(0,0,0,.08);
}
.ribbon::before {
  content: ""; position: absolute; top: 0; left: -4px; width: 4px; height: 4px;
  background: color-mix(in srgb, var(--chip) 60%, #000);
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
}
.card-body { padding: 0 16px; }
h2.term-title {
  margin: 12px 0 8px; padding-left: 10px; border-left: 4px solid var(--navy);
}
h2.term-title .term-name { font-size: 1.25rem; color: var(--navy); }
h2.term-title .term-en { font-weight: 600; color: var(--navy-2); }
.term-meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 0 0 4px; }
.pill-k {
  background: var(--navy); color: var(--on-navy); font-size: 0.72rem; font-weight: 700;
  padding: 3px 10px; border-radius: 6px;
}
.pill-v {
  background: color-mix(in srgb, var(--navy) 9%, var(--surface-1)); color: var(--ink-muted);
  font-size: 0.82rem; padding: 2px 10px; border-radius: 6px;
}
h3.sec { color: var(--navy); display: flex; align-items: center; gap: 6px; font-size: 0.8rem; }
.ico { width: 16px; height: 16px; flex: 0 0 auto; color: var(--navy); }
.def-distinction { position: relative; border-left: 3px solid var(--gold); }
.dist-k {
  display: inline-block; margin-right: 6px; font-size: 0.68rem; font-weight: 700;
  color: #8b4518; border: 1px solid color-mix(in srgb, var(--gold) 50%, var(--hairline));
  border-radius: 4px; padding: 0 5px; vertical-align: 1px;
}
.term-related {
  margin: 12px 0 0; padding: 8px 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  background: var(--surface-2); border-radius: 10px;
}
.term-related .sec-inline { display: inline-flex; align-items: center; gap: 4px; color: var(--navy); font-size: 0.75rem; }
.term-related .sec-inline .ico { width: 14px; height: 14px; }
.rel-chip {
  display: inline-flex; align-items: center; gap: 5px; font-size: 0.82rem;
  padding: 1px 9px 1px 7px; border-radius: 999px; background: var(--surface-1);
  border: 1px solid var(--hairline); color: var(--ink-muted); text-decoration: none;
}
.rel-chip::before {
  content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--dot, var(--text-muted));
}
.rel-chip.plain::before { background: transparent; border: 1px solid var(--text-muted); }
a.rel-chip:hover { border-color: var(--dot); color: var(--ink); }
.term-related a { color: var(--ink-muted); }
.fw-row {
  grid-template-columns: 7.8em 1fr; border: 0; border-radius: 10px;
  padding: 0; margin-bottom: 6px; overflow: hidden; gap: 0;
  background: color-mix(in srgb, var(--org) 6%, var(--surface-1));
}
.fw-row .fw-org {
  background: color-mix(in srgb, var(--org) 16%, var(--surface-1));
  padding: 8px 8px; text-align: center; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 1px;
}
.fw-row .fw-org b { font-size: 0.8rem; color: var(--ink); line-height: 1.3; }
.fw-flag { font-size: 1.15rem; line-height: 1; }
.fw-row ul { padding: 8px 12px 6px 1.6em; }
.org-intl { --org: #2f6fbf; } .org-eu { --org: #c2416b; } .org-us { --org: #2f8a52; }
.org-kr { --org: #c9932a; } .org-uk { --org: #6b4fa8; } .org-std { --org: #2c8a80; } .org-etc { --org: #7a8494; }
.term-fw, .term-refs, .term-explain { border-top: 0; }
.term-refs ol { background: var(--surface-2); border-radius: 10px; padding: 8px 10px; }
.ref-n { background: var(--navy); color: var(--on-navy); }
.term-rel { margin: 12px 0 0; padding-top: 0; border-top: 0; }
details.term-more { margin: 10px 16px 0; }
.bucket-head { border-bottom: 2px solid color-mix(in srgb, var(--chip) 35%, var(--gridline)); }
@media (max-width: 620px) {
  .card-band { padding-right: 108px; }
  .card-band .ch-en { display: none; }
  .ribbon { right: 10px; font-size: 0.68rem; padding: 5px 9px 11px; }
  .fw-row { grid-template-columns: 1fr; }
  .fw-row .fw-org { flex-direction: row; gap: 6px; justify-content: flex-start; text-align: left; }
}

/* 전체 개념 지도 v2 */
.ov-wrap { border-radius: 10px; border: 1px solid var(--gridline); margin-top: 6px; }
svg.ov-map { display: block; width: 100%; min-width: 760px; height: auto; }
.ov-mob { display: none; }
.ov-toggle { display: none; }
@media (max-width: 700px) {
  .ov-desk { display: none; }
  .ov-mob svg.ov-map { min-width: 0; }
  /* 모바일: 지도는 접어 두고 버튼으로 연다 */
  .concept-maps .map-hint, .concept-maps .ov-wrap { display: none; }
  .concept-maps.mob-open .map-hint, .concept-maps.mob-open .ov-wrap { display: block; }
  .concept-maps .map-hint { order: 3; width: 100%; }
  .ov-toggle { order: 2; }
  .concept-maps.mob-open .ov-mob { display: block; }
  .ov-toggle {
    display: inline-block; margin-left: auto; border: 1px solid var(--hairline); background: var(--surface-2);
    color: var(--navy); border-radius: 999px; padding: 4px 12px; font: inherit; font-size: 0.8rem; font-weight: 650;
    cursor: pointer;
  }
}
svg.ov-map .rel-n, svg.ov-map .rel-e, svg.ov-map .ov-hull { transition: opacity .25s; }
svg.ov-map .dim { opacity: .1; }
svg.ov-map .rel-e { opacity: .5; }
svg.ov-map .rel-e.x-reg, svg.ov-map .rel-e.k-contrasts { opacity: 0; }   /* 기본 화면은 구역 안 흐름만 */
svg.ov-map.focused .rel-e:not(.dim), svg.ov-map.hovering .rel-e:not(.hdim) { opacity: 1; }
svg.ov-map .ov-region { transition: opacity .25s; }
svg.ov-map .ov-region.dim { opacity: .35; }
svg.ov-map .ov-spine, svg.ov-map .ov-label, svg.ov-map .ov-island { transition: opacity .25s; }
svg.ov-map .ov-island.dim { opacity: .35; }
svg.ov-map .ov-chip { cursor: pointer; transition: opacity .25s; }
svg.ov-map .ov-chip:hover rect, svg.ov-map .ov-chip:focus-visible rect { filter: brightness(1.12); }
svg.ov-map .ov-chip.on rect { stroke: var(--ink); stroke-width: 1.5; }
svg.ov-map.focused .ov-chip:not(.on) { opacity: .35; }
svg.ov-map .ov-label:hover { text-decoration: underline; }
svg.ov-map .ov-label.dim { opacity: .3; }
svg.ov-map.hovering .hdim { opacity: .12; }
svg.ov-map a.rel-n:hover rect, svg.rel-ego a.rel-n:hover rect { stroke-width: 2; }
svg .rel-n text { pointer-events: none; }

/* 아코디언 카드 — 접힌 한 줄(번호·표제어·영문·정의 한 줄), 펼치면 전체 카드 */
details.term-card { padding: 0; margin-bottom: 6px; }
details.term-card > summary { list-style: none; }
details.term-card > summary::-webkit-details-marker { display: none; }
.card-sum {
  display: flex; align-items: baseline; gap: 10px; cursor: pointer;
  padding: 10px 16px; border-radius: 12px; min-width: 0;
}
.card-sum:hover { background: color-mix(in srgb, var(--ch) 5%, var(--surface-1)); }
.card-sum .term-n {
  flex: 0 0 auto; background: var(--navy); color: var(--on-navy); font-weight: 700; font-size: 0.74rem;
  padding: 1px 8px; border-radius: 6px; font-variant-numeric: tabular-nums; align-self: center;
}
.sum-head { flex: 0 0 auto; font-weight: 700; font-size: 1.02rem; color: var(--ink); letter-spacing: -0.02em; }
.sum-en { flex: 0 0 auto; color: var(--text-muted); font-size: 0.9rem; }
.sum-lead {
  flex: 1 1 auto; min-width: 0; color: var(--text-secondary); font-size: 0.88rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sum-chev {
  flex: 0 0 auto; width: 8px; height: 8px; margin-left: auto; align-self: center;
  border-right: 2px solid var(--text-muted); border-bottom: 2px solid var(--text-muted);
  transform: rotate(45deg); transition: transform .15s;
}
details[open] > .card-sum { padding: 14px 150px 6px 16px; border-radius: 12px 12px 0 0; }
details[open] > .card-sum .sum-head { font-size: 1.28rem; color: var(--navy); }
details[open] > .card-sum .sum-en { font-weight: 600; color: var(--navy-2); font-size: 0.98rem; }
details[open] > .card-sum .sum-lead { display: none; }
details[open] > .card-sum .sum-chev { display: none; }
details.term-card .card-band {
  background: none; border: 0; padding: 0 16px 6px; border-radius: 0;
}
.card-band .term-link { color: var(--text-muted); text-decoration: none; font-weight: 700; }
.card-band .term-link:hover { color: var(--accent); }
details.term-card .ribbon { top: -4px; }
details:not([open]).term-card .ribbon { display: none; }
.toolbar-gap { flex: 1 1 auto; }
@media (max-width: 620px) {
  .sum-lead { display: none; }
  .card-sum { flex-wrap: wrap; row-gap: 2px; }
  details[open] > .card-sum { padding-right: 108px; }
}

/* 오른쪽 용어 목차 — 라이브러리의 오른쪽 연도 목록에 착안 */
.term-rail {
  position: fixed; top: 56px; right: 16px; z-index: 30;
  width: max-content; min-width: 168px; max-width: 230px; max-height: calc(100vh - 72px);
  overflow-y: auto; background: var(--surface-1); border: 1px solid var(--hairline);
  border-radius: 14px; padding: 8px 8px 10px; font-size: 0.8rem;
  box-shadow: 0 4px 18px color-mix(in srgb, var(--ink) 8%, transparent);
  opacity: 0; visibility: hidden; transition: opacity .2s, visibility .2s;
}
.term-rail.in-list, .term-rail.show { opacity: 1; visibility: visible; }
.rail-head {
  display: flex; align-items: center; justify-content: space-between;
  font-weight: 700; color: var(--navy); padding: 2px 6px 6px; border-bottom: 1px solid var(--gridline);
  margin-bottom: 4px;
}
.rail-top {
  display: flex; align-items: center; gap: 7px; padding: 5px 6px; margin-bottom: 4px;
  border-radius: 8px; color: var(--navy); font-weight: 650; text-decoration: none;
  border-bottom: 1px solid var(--gridline);
}
.rail-top:hover { background: var(--surface-2); }
.rail-top-ico {
  width: 8px; height: 8px; margin: 3px 1px 0; border-left: 2px solid var(--navy); border-top: 2px solid var(--navy);
  transform: rotate(45deg);
}
.rail-close { display: none; border: 0; background: none; font-size: 1.2rem; color: var(--text-muted); cursor: pointer; }
.rail-ch > summary {
  list-style: none; display: flex; align-items: center; gap: 6px; cursor: pointer;
  padding: 4px 6px; border-radius: 8px; color: var(--ink-muted); line-height: 1.35;
}
.rail-ch > summary::-webkit-details-marker { display: none; }
.rail-ch > summary:hover { background: var(--surface-2); }
.rail-ch > summary span { flex: 1 1 auto; min-width: 0; }
.rail-ch > summary b { font-weight: 500; color: var(--text-muted); font-size: 0.72rem; }
.rail-ch .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--chip); flex: 0 0 auto; }
.rail-ch.cur > summary { background: color-mix(in srgb, var(--chip) 12%, var(--surface-1)); color: var(--ink); font-weight: 650; }
.rail-ch ul { list-style: none; margin: 2px 0 6px; padding: 0 0 0 20px; border-left: 2px solid color-mix(in srgb, var(--chip) 35%, transparent); margin-left: 9px; }
.rail-ch li a {
  display: block; padding: 2px 6px; color: var(--text-secondary); text-decoration: none;
  border-radius: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.rail-ch li a:hover { background: var(--surface-2); color: var(--ink); }
.rail-fab { display: none; }
@media (max-width: 1459px) {
  .term-rail { display: none; top: auto; bottom: 70px; max-height: min(70vh, 560px); max-width: min(280px, calc(100vw - 32px)); }
  .term-rail.show { display: block; }
  .rail-close { display: block; }
  .rail-fab {
    display: block; position: fixed; right: 16px; bottom: 16px; z-index: 31;
    background: var(--navy); color: var(--on-navy); border: 0; border-radius: 999px;
    padding: 10px 16px; font: inherit; font-size: 0.85rem; font-weight: 700; cursor: pointer;
    box-shadow: 0 4px 14px color-mix(in srgb, var(--ink) 25%, transparent);
  }
}
"""


def page(title, current, body, *, head_count=None, extra_js=""):
    return ui.page(title, current, body, css=GLOSSARY_CSS, head_count=head_count, extra_js=extra_js)


LIBRARY_DOC_URL = series.url("library") + "#{}"
DIGEST_DAY_URL = series.url("digest") + "daily/{}.html"
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


def sibling_html(e):
    """형제 사이트 연결 — AI 안전 연구 카탈로그의 연구, AI 안전 라이브러리의 정책 문서."""
    out = []
    if e.get("research"):
        lis = "".join(
            '<li><span class="ex-date">{d}</span><span><a href="{u}" target="_blank" rel="noopener">{t}</a>'
            ' <span class="ex-src">{s}</span></span></li>'.format(
                d=html.escape((x.get("date") or "")[:10]), u=html.escape(x["url"]),
                t=html.escape(x["title"]), s=html.escape((x.get("source") or "")[:24]))
            for x in e["research"])
        out.append(f'<div class="term-examples"><p class="ex-label">관련 연구 · '
                   f'<a href="{html.escape(series.url("research"))}" target="_blank" rel="noopener">AI 안전 연구</a></p>'
                   f'<ol>{lis}</ol></div>')
    if e.get("library_docs"):
        lis = "".join(
            '<li><span class="ex-date">{d}</span><span>{f}<a href="{u}" target="_blank" rel="noopener">{t}</a>'
            ' <span class="ex-src">{o}</span></span></li>'.format(
                d=html.escape((x.get("date") or "")[:10]), f=(html.escape(x["flag"]) + " ") if x.get("flag") else "",
                u=html.escape(LIBRARY_DOC_URL.format(x["id"])), t=html.escape(x["title"]),
                o=html.escape(" · ".join(v for v in (x.get("org"), x.get("kind")) if v)[:30]))
            for x in e["library_docs"])
        out.append(f'<div class="term-examples"><p class="ex-label">관련 정책 문서 · '
                   f'<a href="{html.escape(series.url("library"))}" target="_blank" rel="noopener">AI 안전 라이브러리</a></p>'
                   f'<ol>{lis}</ol></div>')
    return "".join(out)


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


REL_CTX = {"nodes": {}, "color": {}, "layouts": {}}
REL_DIRS = (("up", "상위"), ("down", "하위"), ("pre", "먼저 알 개념"), ("prev", "앞 단계"),
            ("next", "다음 단계"), ("vs", "혼동 주의"))


def rel_section(e):
    """카드 안 관계도 자리. 배치는 REL_CTX["layouts"]에 모아 docs/rel.js 로 내보내고,
    카드를 펼칠 때 JS(drawEgo)가 그린다. JS가 없으면 이웃 용어 목록(글)이 그대로 보인다."""
    lay = relmap.ego_layout(e, REL_CTX["nodes"])
    if not lay:
        return ""
    REL_CTX["layouts"][e["id"]] = relmap.ego_layout_compact(lay)
    nodes = REL_CTX["nodes"]
    parts = []
    for k, label in REL_DIRS:
        ids = [i for i in (e.get("rel") or {}).get(k) or [] if i in nodes]
        if ids:
            parts.append(f'<span><b>{label}</b> ' + ", ".join(
                f'<a href="#{html.escape(i)}">{html.escape(nodes[i]["head"])}</a>' for i in ids) + '</span>')
    fallback = f'<p class="rel-list">{" · ".join(parts)}</p>'
    return (f'<section class="term-rel"><h3 class="sec">{icon("rel")}용어 관계</h3>'
            f'<div class="rel-scroll rel-mount" data-rel="{html.escape(e["id"])}">{fallback}</div></section>')


ORG_TYPES = [  # (판별어, 유형) — 앞에서부터 맞춘다
    (("EU",), "eu"), (("NIST", "미국"), "us"), (("한국", "과기정통부", "인공지능기본법"), "kr"),
    (("UK", "영국"), "uk"), (("ISO", "IEC", "IEEE"), "std"),
    (("OECD", "국제", "UN", "싱가포르", "G7"), "intl"),
]
ORG_FLAG = {"intl": "🌐", "eu": "🇪🇺", "us": "🇺🇸", "kr": "🇰🇷", "uk": "🇬🇧", "std": "📐", "etc": "📄"}


def org_type(org):
    for keys, t in ORG_TYPES:
        if any(k in org for k in keys):
            return t
    return "etc"


def icon(name):
    """소제목 아이콘 — 인쇄 카드의 문서·기관·책 아이콘에 맞춘 단순 선 그림."""
    paths = {
        "doc": '<path d="M6 2h7l5 5v15H6z"/><path d="M13 2v5h5M9 12h6M9 16h6"/>',
        "rel": '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M11 7.3 6.2 16.8M13 7.3l4.8 9.5M7.5 19h9"/>',
        "inst": '<path d="M3 9 12 4l9 5M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/>',
        "book": '<path d="M12 6c-2-1.5-5-2-8-1.5V19c3-.5 6 0 8 1.5 2-1.5 5-2 8-1.5V4.5c-3-.5-6 0-8 1.5zM12 6v14.5"/>',
        "hash": '<path d="M9 3 7 21M17 3l-2 18M4 9h17M3 15h17"/>',
    }
    return (f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>')


def card_html(e):
    cid = e["id"]
    d = e.get("definition") or {}
    alts = e.get("alternatives") or []

    meta = ""
    if alts:
        alt_s = "".join(
            f'<span class="pill-v" title="{html.escape(SOURCE_LABEL.get(a.get("source"), ""))}">{html.escape(a["text"])}</span>'
            for a in alts)
        meta = f'<div class="term-meta"><span class="pill-k">대체어</span>{alt_s}</div>'

    explain = []
    if d.get("lead"):
        explain.append(f'<p class="def-lead">{ui.prose_with_emphasis(d["lead"])}</p>')
    if d.get("points"):
        explain.append('<ul class="def-points">' + "".join(
            f"<li>{ui.prose_with_emphasis(p)}</li>" for p in d["points"]) + "</ul>")
    dist = d.get("distinction")
    if dist and dist.get("text"):
        explain.append(f'<p class="def-distinction"><span class="dist-k">구별</span>'
                       f'{ui.prose_with_emphasis(dist["text"])}</p>')

    related = ""
    if e.get("related"):
        tags = []
        for r in e["related"]:
            if r.get("id"):
                col = REL_CTX["color"].get(r["id"], "var(--text-muted)")
                tags.append(f'<a class="rel-chip" href="#{html.escape(r["id"])}" style="--dot:{col}">'
                            f'{html.escape(nospace(r["head"]))}</a>')
            else:
                tags.append(f'<span class="rel-chip plain">{html.escape(nospace(r["label"]))}</span>')
        related = (f'<div class="term-related"><span class="sec-inline">{icon("hash")}관련 용어</span>'
                   f'{"".join(tags)}</div>')

    fw = ""
    if e.get("frameworks"):
        rows = []
        for f in e["frameworks"]:
            t = org_type(f.get("org", ""))
            pts = "".join(
                f'<li>{ui.prose_with_emphasis(p["text"] if isinstance(p, dict) else p)}'
                f'{ref_sup(cid, p.get("refs") if isinstance(p, dict) else None)}</li>'
                for p in f.get("points") or [])
            rows.append(
                f'<div class="fw-row org-{t}"><div class="fw-org"><span class="fw-flag">{ORG_FLAG[t]}</span>'
                f'<b>{html.escape(f.get("org", ""))}</b>'
                f'{("<span>" + html.escape(str(f["sub"])) + "</span>") if f.get("sub") else ""}</div>'
                f'<ul>{pts}</ul></div>')
        fw = (f'<section class="term-fw"><h3 class="sec">{icon("inst")}주요 기관·문서별 개념 및 적용</h3>'
              f'{"".join(rows)}</section>')

    refs = ""
    if e.get("refs"):
        lis = "".join(
            f'<li id="{html.escape(cid)}-ref-{r.get("n")}"><span class="ref-n">{r.get("n")}</span>'
            f'<span>{html.escape(r.get("text", ""))}'
            f'{(" · " + html.escape(r["evidence"]["pages"])) if (r.get("evidence") or {}).get("pages") and r["evidence"]["pages"] not in r.get("text", "") else ""}'
            f'{(" · <a href=" + chr(34) + html.escape(r["url"]) + chr(34) + " target=_blank rel=noopener>원문</a>") if r.get("url") else ""}'
            f'{library_link(r.get("library_id"))}</span></li>'
            for r in e["refs"])
        refs = f'<section class="term-refs"><h3 class="sec">{icon("book")}출처</h3><ol>{lis}</ol></section>'

    rel = rel_section(e)

    more = []
    if e.get("commentary"):
        more.append('<p class="section-label">해설</p><div class="term-commentary">' + "".join(
            f'<p>{ui.prose_with_emphasis(p)}</p>' for p in e["commentary"]) + "</div>")
    if e.get("pdf_definitions"):
        more.append('<p class="section-label">PDF 원문 인용</p>' + pdf_quotes_html(e["pdf_definitions"]))
    more.append(examples_html(e.get("examples")))
    more.append(sibling_html(e))
    if e.get("variants"):
        more.append("".join(
            f'<div class="term-variants">{k} 표기 · {html.escape(v)}</div>' for k, v in e["variants"]))
    more.append(metrics_html(e))
    more_s = "".join(x for x in more if x)
    more_label = []
    if e.get("commentary"):
        more_label.append("해설")
    if e.get("pdf_definitions"):
        more_label.append(f"원문 인용 {len(e['pdf_definitions'])}")
    if e.get("examples"):
        more_label.append(f"참고 기사 {len(e['examples'])}")
    if e.get("research"):
        more_label.append(f"관련 연구 {len(e['research'])}")
    if e.get("library_docs"):
        more_label.append(f"정책 문서 {len(e['library_docs'])}")
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

    side = fw + refs
    main = (f'{meta}'
            f'<section class="term-explain"><h3 class="sec">{icon("doc")}용어 설명</h3>{"".join(explain)}</section>'
            f'{related}{rel}')
    lead_short = d.get("lead") or ""
    return (
        f'<details class="term-card" id="{html.escape(cid)}" data-cat="{e["category"]}" '
        f'data-ch="{e["chapter"]}" data-n="{e["n"]}" data-head="{html.escape(e["head"])}" '
        f'data-q="{html.escape(" ".join(q_bits).lower())}" '
        f'data-qn="{html.escape(nospace(" ".join([e["head"], e["en"]] + [a["text"] for a in alts])).lower())}" '
        f'style="--chip:{html.escape(e["color"])};--ch:{html.escape(e.get("chapter_color") or e["color"])}">'
        f'<summary class="card-sum"><span class="term-n">{e["n"]:03d}</span>'
        f'<span class="sum-head">{html.escape(e["head"])}</span>'
        f'<span class="sum-en">{html.escape(e["en"])}</span>'
        f'<span class="sum-lead">{ui.prose_with_emphasis(lead_short)}</span>'
        f'<span class="sum-chev" aria-hidden="true"></span></summary>'
        f'<div class="card-open">'
        f'<div class="card-band"><a class="term-link" href="#{html.escape(cid)}" title="이 용어 링크">#</a>'
        f'<span class="card-chapter">{e["chapter"]}. {html.escape(e["chapter_label"])}'
        f' <span class="ch-en">{html.escape(e["chapter_en"])}</span></span></div>'
        f'<span class="ribbon">{html.escape(e["category_label"])}</span>'
        f'<div class="card-body">{main}{side}</div>'
        f"{more_html}"
        f"</div></details>"
    )

LEGEND = """<details class="legend">
<summary>카드 읽는 법</summary>
<table>
<tr><td>표제어</td><td>번역 용어 정본(ai-safety-translation-kit)의 번역어를 기본으로 한다. '안전', '위험', '사고'처럼 AI를 붙이지 않고 쓰며, 'AI 안전' 같은 표기는 대체어로 둔다.</td></tr>
<tr><td>대체어</td><td>함께 쓰이는 다른 표기. 마우스를 올리면 출처(정본 변형·이전 표기·편집)가 보인다.</td></tr>
<tr><td>용어 설명</td><td>굵은 한 줄이 정의, 아래 항목이 AI 안전 관점의 부연, 회색 상자가 헷갈리기 쉬운 용어와의 구별이다.</td></tr>
<tr><td>기관·문서별</td><td>국제기구·표준·법령이 그 개념을 어떻게 정의하고 적용하는지. 번호는 출처 목록을 가리킨다.</td></tr>
<tr><td>용어 관계</td><td>가운데가 이 용어. 위는 상위어, 아래는 하위어, 왼쪽은 먼저 알 개념·앞 단계, 오른쪽은 다음 단계·혼동 주의 용어다. 상자를 누르면 그 카드로 간다.</td></tr>
<tr><td>펼치기</td><td>해설, PDF 원문 인용(쪽수), 다이제스트 참고 기사, 코퍼스 지표.</td></tr>
</table>
</details>"""


EGO_JS = """<script>
/* 카드 안 관계도 — docs/rel.js(window.__REL__)의 배치를 relmap.ego_draw 와 같은 마크업으로 그린다.
   window.drawEgo(termId, container) → 그렸으면 true. 데이터가 아직 없으면 false. */
(function () {
  function f1(v) { return Number(v).toFixed(1); }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  var KIND = { b: 'broader', l: 'leads_to', r: 'requires', c: 'contrasts' };
  function defs(p) {
    return '<defs>' +
      '<marker id="' + p + '-a1" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--ink-muted)"/></marker>' +
      '<marker id="' + p + '-a2" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0.6 L7.4,4 L0,7.4 z" style="fill:var(--text-muted);opacity:.75"/></marker>' +
      '</defs>';
  }
  function curve(x1, y1, x2, y2, bend) {
    var mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
    var L = Math.hypot(dx, dy) || 1, k = bend * Math.min(L, 260);
    var cx = mx - dy / L * k, cy = my + dx / L * k;
    return 'M' + f1(x1) + ',' + f1(y1) + ' Q' + f1(cx) + ',' + f1(cy) + ' ' + f1(x2) + ',' + f1(y2);
  }
  function edge(kind, x1, y1, x2, y2, p) {
    var attrs = 'class="rel-e k-' + kind + '" data-a="" data-b=""';
    if (kind === 'contrasts') {
      var mx = x1 + (x2 - x1) * 0.62, my = y1 + (y2 - y1) * 0.62;
      return '<g ' + attrs + '><path d="' + curve(x1, y1, x2, y2, 0) + '" style="fill:none;stroke:var(--accent);stroke-width:1;stroke-opacity:.45;stroke-dasharray:1 3"/>' +
        '<circle cx="' + f1(mx) + '" cy="' + f1(my) + '" r="7.5" style="fill:var(--surface-1);stroke:var(--accent);stroke-width:1"/>' +
        '<text x="' + f1(mx) + '" y="' + f1(my + 3.6) + '" text-anchor="middle" font-size="10.5" style="fill:var(--accent);font-weight:700">\\u2260</text></g>';
    }
    if (kind === 'broader') {
      return '<path ' + attrs + ' d="' + curve(x1, y1, x2, y2, 0) + '" style="fill:none;stroke:var(--text-muted);stroke-width:1;stroke-opacity:.45"/>';
    }
    var st = kind === 'leads_to' ? 'stroke:var(--ink-muted);stroke-width:1.5;stroke-opacity:.8' : 'stroke:var(--text-muted);stroke-width:1.2;stroke-opacity:.6';
    var mk = kind === 'leads_to' ? p + '-a1' : p + '-a2';
    return '<path ' + attrs + ' d="' + curve(x1, y1, x2, y2, 0.14) + '" style="fill:none;' + st + '" marker-end="url(#' + mk + ')"/>';
  }
  function node(id, meta, cx, cy, w, center) {
    var head = meta[0], en = meta[1], color = meta[2] || 'var(--navy)';
    var x = cx - w / 2, y = cy - 13, rect, txt;
    if (center) {
      rect = '<rect x="' + f1(x) + '" y="' + f1(y) + '" width="' + f1(w) + '" height="26" rx="13.0" style="fill:' + color + '"/>';
      txt = 'style="fill:#fff;font-weight:700"';
    } else {
      rect = '<rect x="' + f1(x) + '" y="' + f1(y) + '" width="' + f1(w) + '" height="26" rx="13.0" ' +
        'style="fill:color-mix(in srgb, ' + color + ' 20%, var(--surface-1));stroke:color-mix(in srgb, ' + color + ' 60%, transparent);stroke-width:1.1"/>';
      txt = 'style="fill:var(--ink);font-weight:500"';
    }
    var t = '<text x="' + f1(cx) + '" y="' + f1(cy + 4.3) + '" text-anchor="middle" font-size="12.5" ' + txt + '>' + esc(head) + '</text>';
    if (center) return '<g class="rel-n rel-center">' + rect + t + '</g>';
    return '<a class="rel-n" data-id="' + esc(id) + '" href="#' + esc(id) + '"><title>' + esc(head + ' \\u00b7 ' + en) + '</title>' + rect + t + '</a>';
  }
  function label(x, y, s, anchor) {
    return '<text x="' + f1(x) + '" y="' + f1(y) + '" text-anchor="' + anchor + '" font-size="10.5" style="fill:var(--text-muted);font-weight:600;letter-spacing:.02em">' + esc(s) + '</text>';
  }
  window.drawEgo = function (id, el) {
    var R = window.__REL__;
    if (!R || !R.t || !R.t[id]) return false;
    var lay = R.t[id], N = R.n, p = 'e-' + id, cm = N[id] || [id, '', ''];
    var out = ['<svg class="rel-ego" viewBox="0 0 ' + lay.w + ' ' + lay.h + '" role="img" aria-label="' + esc(cm[0]) + ' \\uad00\\uacc4\\ub3c4">', defs(p)];
    lay.l.forEach(function (l) { out.push(label(l[0], l[1], l[2], l[3])); });
    lay.e.forEach(function (e) { out.push(edge(KIND[e[0]], e[1], e[2], e[3], e[4], p)); });
    lay.n.forEach(function (n) { out.push(node(n[0], N[n[0]] || [n[0], '', ''], n[1], n[2], n[3], false)); });
    out.push(node(id, cm, lay.c[1], lay.c[2], lay.c[3], true), '</svg>');
    el.innerHTML = out.join('');
    return true;
  };
})();
</script>"""

OVERVIEW_JS = """<script>
Array.prototype.forEach.call(document.querySelectorAll('svg.ov-map'), function (svg) {
  var themes = JSON.parse(document.getElementById('mapThemes').textContent);
  var nodes = Array.prototype.slice.call(svg.querySelectorAll('.rel-n[data-id]'));
  var edges = Array.prototype.slice.call(svg.querySelectorAll('.rel-e'));
  var hulls = Array.prototype.slice.call(svg.querySelectorAll('.ov-hull'));
  var regions = Array.prototype.slice.call(svg.querySelectorAll('.ov-region'));
  var spines = Array.prototype.slice.call(svg.querySelectorAll('.ov-spine'));
  var labels = Array.prototype.slice.call(svg.querySelectorAll('.ov-label'));
  var islands = Array.prototype.slice.call(svg.querySelectorAll('.ov-island'));
  var centers = Array.prototype.slice.call(svg.querySelectorAll('.ov-center')).map(function (n) { return n.getAttribute('data-id'); });
  labels.forEach(function (lb) {
    lb.addEventListener('click', function () {
      var b = document.querySelector('button.map-tab[data-theme="' + lb.getAttribute('data-theme') + '"]');
      if (b) b.click();
    });
  });
  function fit(b) {                       // 구역을 지도 비율에 맞춰 여백과 함께 확대
    var pad = 12, w = b[2] + pad * 2, h = b[3] + pad * 2, ratio = full[2] / full[3];
    if (w / h > ratio) h = w / ratio; else w = h * ratio;
    return [b[0] + b[2] / 2 - w / 2, b[1] + b[3] / 2 - h / 2, w, h];
  }
  var full = svg.getAttribute('data-full').split(' ').map(Number);
  var cur = full.slice(), anim = null, focus = null;
  var nb = {};
  edges.forEach(function (e) {
    var a = e.getAttribute('data-a'), b = e.getAttribute('data-b');
    (nb[a] = nb[a] || []).push(b); (nb[b] = nb[b] || []).push(a);
  });
  function paint(set, cls) {
    nodes.forEach(function (n) { n.classList.toggle(cls, !!set && !set[n.getAttribute('data-id')]); });
    edges.forEach(function (e) {
      var on = set && set[e.getAttribute('data-a')] && set[e.getAttribute('data-b')];
      e.classList.toggle(cls, !!set && !on);
    });
    spines.forEach(function (sp) {
      var on = set && set[sp.getAttribute('data-a')] && set[sp.getAttribute('data-b')];
      sp.classList.toggle(cls, !!set && !on);
    });
    labels.forEach(function (lb) {
      if (cls === 'dim') lb.classList.toggle(cls, !!set && lb.getAttribute('data-theme') !== curTheme);
    });
    islands.forEach(function (il) {
      if (cls === 'dim') il.classList.toggle(cls, !!set && il.getAttribute('data-theme') !== curTheme);
    });
    hulls.forEach(function (h) {
      var ids = h.getAttribute('data-ids').split(' ');
      var any = set && ids.some(function (i) { return set[i]; });
      h.classList.toggle(cls, !!set && !any);
    });
  }
  var curTheme = '';
  function zoom(to) {
    if (anim) cancelAnimationFrame(anim);
    var from = cur.slice(), t0 = performance.now(), dur = 420;
    (function step(t) {
      var k = Math.min(1, (t - t0) / dur); k = 1 - Math.pow(1 - k, 3);
      cur = from.map(function (v, i) { return v + (to[i] - v) * k; });
      svg.setAttribute('viewBox', cur.map(function (v) { return v.toFixed(1); }).join(' '));
      if (k < 1) anim = requestAnimationFrame(step);
    })(t0);
  }
  function bbox(set) {
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    nodes.forEach(function (n) {
      if (!set[n.getAttribute('data-id')]) return;
      var b = n.getBBox();
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
    });
    var pad = 46, w = x1 - x0 + pad * 2, h = y1 - y0 + pad * 2;
    var ratio = full[2] / full[3];               // 지도 비율을 지켜 확대
    if (w / h > ratio) h = w / ratio; else w = h * ratio;
    var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    return [cx - w / 2, cy - h / 2, w, h];
  }
  function focusTheme(theme) {
    document.querySelectorAll('button.map-tab').forEach(function (o) { o.classList.toggle('active', (o.dataset.theme || '') === (theme || '')); });
    svg.querySelectorAll('.ov-chip').forEach(function (c) { c.classList.toggle('on', c.getAttribute('data-theme') === theme); });
    var b = { dataset: { theme: theme || '' } };
    (function () {
      var t = themes[b.dataset.theme];
      curTheme = b.dataset.theme;
      if (!t) {
        focus = null; paint(null, 'dim'); svg.classList.remove('focused'); zoom(full);
        regions.forEach(function (r) { r.classList.remove('dim'); }); return;
      }
      focus = {}; t.terms.forEach(function (i) { focus[i] = 1; });
      centers.forEach(function (c) { focus[c] = 1; });
      paint(focus, 'dim'); svg.classList.add('focused');
      var rg = svg.querySelector('.ov-region[data-theme="' + b.dataset.theme + '"]');
      zoom(rg ? fit(rg.getAttribute('data-box').split(' ').map(Number)) : bbox(focus));
      regions.forEach(function (r) { r.classList.toggle('dim', r !== rg); });
    })();
  }
  document.querySelectorAll('button.map-tab').forEach(function (b) {
    b.addEventListener('click', function () { focusTheme(b.dataset.theme || ''); });
  });
  svg.addEventListener('click', function (ev) {   // 확대된 상태에서 빈 곳을 누르면 전체로
    if (!curTheme) return;
    if (ev.target.closest('.ov-chip, .rel-n')) return;
    focusTheme('');
  });
  svg.querySelectorAll('.ov-chip').forEach(function (c) {
    function go() { var th = c.getAttribute('data-theme'); focusTheme(curTheme === th ? '' : th); }
    c.addEventListener('click', go);
    c.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(); } });
  });
  nodes.forEach(function (n) {
    n.addEventListener('mouseenter', function () {
      var id = n.getAttribute('data-id'), set = {}; set[id] = 1;
      (nb[id] || []).forEach(function (j) { set[j] = 1; });
      svg.classList.add('hovering'); paint(set, 'hdim');
    });
    n.addEventListener('mouseleave', function () { svg.classList.remove('hovering'); paint(null, 'hdim'); });
  });
});
</script>"""


def concept_maps_html(data):
    """맨 위 전체 개념 지도 + 장 버튼(누르면 그 장만 강조하고 확대)."""
    lpath = os.path.join(config.DATA, "overview_layout.json")
    if not os.path.exists(lpath):
        return ""
    layout = json.load(open(lpath, encoding="utf-8"))
    edges = [tuple(x) for x in data.get("relations") or []]
    deg = {}
    for a, _, b in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    color = lambda i: REL_CTX["color"].get(i, "var(--navy)")
    chap_label = {c["no"]: c["label"] for c in data["chapters"]}
    svg = relmap.overview_svg(layout, REL_CTX["nodes"], edges, color, deg, chap_label)
    if layout.get("mobile"):   # 모바일: 섬을 한 줄로 쌓은 배치를 따로 그린다
        mob = {**layout, **layout["mobile"]}
        svg = (f'<div class="ov-desk">{svg}</div><div class="ov-mob">'
               + relmap.overview_svg(mob, REL_CTX["nodes"], edges, color, deg, chap_label, "ovMapM", "ovm")
               + '</div>')
    home = layout.get("home") or {}
    tdata = {}
    for c in data["chapters"]:
        terms = [i for i, h in home.items() if h == c["no"]]
        if not terms:
            continue
        tdata[c["no"]] = {"terms": terms}
    return (f'<section class="concept-maps" aria-label="개념 지도">'
            f'<div class="map-head"><h2>개념 지도</h2><span class="map-hint">장 이름표를 누르면 그 장이 확대되고, 다시 누르거나 빈 곳을 누르면 돌아옵니다.</span><button type="button" class="ov-toggle" id="ovToggle" aria-expanded="false">개념 지도 펼치기</button></div>'
            f'<div class="rel-scroll ov-wrap">{svg}</div>'
            f'<script id="mapThemes" type="application/json">{chrome.safe_json(tdata)}</script>'
            f'</section>')


def rail_html(data):
    """오른쪽 목차 — 장(색 점) ⊃ 용어. 누르면 그 카드를 펼치며 이동."""
    groups = []
    for c in data["chapters"]:
        items = [e for e in data["entries"] if e["chapter"] == c["no"]]
        if not items:
            continue
        lis = "".join(f'<li><a href="#{html.escape(e["id"])}">{html.escape(e["head"])}</a></li>' for e in items)
        groups.append(
            f'<details class="rail-ch" data-ch="{c["no"]}" style="--chip:{c["color"]}">'
            f'<summary><i class="dot"></i><span>{c["no"]}. {html.escape(c["label"])}</span>'
            f'<b>{len(items)}</b></summary><ul>{lis}</ul></details>')
    return (f'<nav class="term-rail" id="termRail" aria-label="용어 목차">'
            f'<div class="rail-head"><span>용어 목차</span>'
            f'<button type="button" class="rail-close" id="railClose" aria-label="목차 닫기">×</button></div>'
            f'<a class="rail-top" href="#" id="railTop"><span class="rail-top-ico" aria-hidden="true"></span>맨 위로</a>'
            f'{"".join(groups)}</nav>'
            f'<button type="button" class="rail-fab" id="railFab" aria-controls="termRail">목차</button>')


def index_page(data):
    ents = data["entries"]
    cats = data["categories"]
    chs = data["chapters"]
    cat_color = {c["code"]: c["color"] for c in cats}
    cat_chips = "".join(
        f'<button class="filter-chip" data-cat="{c["code"]}">'
        f'{html.escape(c["label"])} <span class="n">{c["n"]}</span></button>'
        for c in cats if c["n"])
    ch_chips = "".join(
        f'<button class="filter-chip" data-ch="{c["no"]}" data-chcat="{c["category"]}" '
        f'style="--chip:{c["color"]}"><i class="dot"></i>{c["no"]}. {html.escape(c["label"])} '
        f'<span class="n">{c["n"]}</span></button>'
        for c in chs if c["n"])
    sorts = [("ch", "장순"), ("ko", "가나다")]
    sort_chips = "".join(
        f'<button class="filter-chip{" active" if k == "ch" else ""}" data-sort="{k}">{html.escape(lb)}</button>'
        for k, lb in sorts)
    ch_meta = {c["no"]: {"label": c["label"], "en": c["en"], "cat": c["category"],
                         "color": c["color"]} for c in chs}
    cat_label = {c["code"]: c["label"] for c in cats}
    legacy_path = os.path.join(config.DATA, "legacy_anchors.json")
    legacy = json.load(open(legacy_path, encoding="utf-8"))["map"] if os.path.exists(legacy_path) else {}
    REL_CTX["nodes"] = {e["id"]: {"id": e["id"], "head": e["head"], "en": e["en"]} for e in ents}
    REL_CTX["color"] = {e["id"]: e["color"] for e in ents}
    for e in ents:
        e["chapter_color"] = e["color"]
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
    <span class="toolbar-gap"></span>
    <button class="filter-chip" id="toggleAll" type="button">모두 펼치기</button>
  </div>
</div>
<p class="result-line" id="resultLine" data-corpus="{corpus_note}">{len(ents)}개 표제어</p>
<div id="termList">{cards}</div>
{rail_html(data)}
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
    el.open = true;
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
  // 오른쪽 목차: 넓은 화면은 고정, 좁은 화면은 버튼으로 연다. 지금 보는 장을 표시한다.
  var rail = document.getElementById('termRail');
  var fab = document.getElementById('railFab');
  if (rail) {
    fab.addEventListener('click', function () { rail.classList.toggle('show'); });
    document.getElementById('railClose').addEventListener('click', function () { rail.classList.remove('show'); });
    document.getElementById('railTop').addEventListener('click', function (ev) {
      ev.preventDefault();
      history.replaceState(null, '', location.pathname + location.search);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      rail.classList.remove('show');
    });
    rail.addEventListener('click', function (ev) {
      var a = ev.target.closest('a[href^="#"]');
      if (a && window.matchMedia('(max-width: 1459px)').matches) rail.classList.remove('show');
    });
    var groups = Array.prototype.slice.call(rail.querySelectorAll('.rail-ch'));
    var curCh = null;
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (!en.isIntersecting) return;
        var ch = en.target.dataset.ch;
        if (ch === curCh) return;
        curCh = ch;
        groups.forEach(function (g) { g.classList.toggle('cur', g.dataset.ch === ch); });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    cards.forEach(function (c) { io.observe(c); });
    // 넓은 화면에서도 목차는 용어 목록에 도달한 뒤에만 보인다 (넓은 개념 지도와 겹치지 않게)
    var ctl = document.getElementById('listControls');
    var io2 = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) { rail.classList.toggle('in-list', en.boundingClientRect.top < window.innerHeight * 0.6); });
    }, { threshold: [0, 1] });
    io2.observe(ctl);
    function railVis() { rail.classList.toggle('in-list', ctl.getBoundingClientRect().top < window.innerHeight * 0.6); }
    window.addEventListener('scroll', railVis, { passive: true }); railVis();
  }
  // 카드 안 관계도: 펼칠 때 한 번만 그린다 (reveal·모두 펼치기·사용자 클릭 모두 toggle 이벤트로 온다)
  function drawRel(card) {
    var m = card.querySelector('.rel-mount[data-rel]');
    if (!m || m.dataset.done) return;
    if (window.drawEgo && window.drawEgo(m.dataset.rel, m)) m.dataset.done = '1';
  }
  cards.forEach(function (c) { c.addEventListener('toggle', function () { if (c.open) drawRel(c); }); });
  window.__onRel__ = function () { cards.forEach(function (c) { if (c.open) drawRel(c); }); };  // rel.js 가 늦게 오면
  if (window.__REL__) window.__onRel__();
  var tAll = document.getElementById('toggleAll');
  if (tAll) tAll.addEventListener('click', function () {
    var open = tAll.dataset.open !== '1';
    cards.forEach(function (c) { if (!c.classList.contains('hidden')) c.open = open; });
    tAll.dataset.open = open ? '1' : '';
    tAll.textContent = open ? '모두 접기' : '모두 펼치기';
  });
  var ovT = document.getElementById('ovToggle');
  if (ovT) ovT.addEventListener('click', function () {
    var sec = ovT.closest('.concept-maps');
    var open = sec.classList.toggle('mob-open');
    ovT.setAttribute('aria-expanded', open ? 'true' : 'false');
    ovT.textContent = open ? '접기' : '개념 지도 펼치기';
  });
  // 새로 고침은 늘 맨 위(개념 지도)에서 시작한다. 공유 링크(#용어)로 처음 들어올 때만 그 카드로 간다
  var navType = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0] || {}).type;
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  if (navType === 'reload' && location.hash) history.replaceState(null, '', location.pathname + location.search);
  window.addEventListener('hashchange', onHash);
  apply();
  onHash();
  // 카드 재배치·웹폰트 적용 뒤에 위치가 밀리므로 load 뒤 한 번 더 맞춘다
  window.addEventListener('load', function () { setTimeout(onHash, 0); });
})();
</script>"""
    js = js + EGO_JS + OVERVIEW_JS + '<script defer src="rel.js"></script>'
    js = (js.replace("__CH__", chrome.safe_json(ch_meta))
            .replace("__CAT__", chrome.safe_json(cat_label))
            .replace("__LEGACY__", chrome.safe_json(legacy)))
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
<li><b>표제어에 AI를 붙이지 않습니다.</b> '안전', '위험', '사고', '역량'처럼 쓰고, 'AI 안전'·'AI 사고' 같은 표기는
대체어로 함께 적어 검색에 걸리게 했습니다. 다만 'AI 에이전트', 'AI 거버넌스', 'AI 윤리'처럼 AI가 붙은 채 굳은 이름은 그대로 씁니다.</li>
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
기만·오정렬 → 계략적 행동), <b>혼동 주의</b>(허위 정보 ↔ 오정보). 맨 위 개념 지도는 핵심 용어를
한 장에 펼친 것입니다. 가운데에 AI 위험과 AI 안전을 두고, 장마다 부채꼴 하나를 주었습니다. 왼쪽은
위험·사고(03~07장), 오른쪽은 평가·안전 대책과 거버넌스·제도(08~11장), 위쪽은 그 바탕인 기술과 역량(01·02장)입니다.
색은 장을 뜻하며, 카드 리본·필터·오른쪽 목차에도 같은 색을 씁니다.
가운데에서 뻗는 굵은 가지는 지도의 뼈대일 뿐 관계 데이터가 아닙니다. 카드마다 있는 <b>용어 관계</b> 그림은
그 용어 주변만 보여 줍니다.
관계는 현재 {data.get('meta', {}).get('counts', {}).get('relations', 0)}개입니다.</p>

<h2>근거 자료와 다른 사이트</h2>
<table>
<tr><th>자료</th><th>용어집에서 쓰는 곳</th></tr>
<tr><td><a href="{series.url("digest")}" target="_blank" rel="noopener">AI 안전 다이제스트</a></td>
<td>매일 모으는 뉴스·정책 동향. 표제어 후보 추출과 <b>참고 기사</b>의 출처입니다
(빌드 시점 {docs:,}건, {html.escape(str(c.get('from', '')))} ~ {html.escape(str(c.get('to', '')))}).
기사마다 원문 링크와 함께 그 기사가 실린 다이제스트 날짜 페이지를 잇습니다.</td></tr>
<tr><td><a href="{series.url("research")}" target="_blank" rel="noopener">AI 안전 연구</a></td>
<td>AI 안전 연구 카탈로그. 용어 표기로 연구 제목(없으면 요약)을 찾아 카드의 <b>관련 연구</b>에 최근 것부터 4건까지 잇습니다
(현재 {cnt.get('linked', {}).get('with_research', 0)}개 표제어). 참고 기사 가운데 <span class="ex-tag">연구</span> 표시는 다이제스트가 모은 연구 문헌입니다.</td></tr>
<tr><td>PDF 근거 색인</td>
<td>국제 보고서·법령·가이드라인 PDF를 쪽 단위로 색인한 연구소 내부 자료(PDF Evidence Desk)입니다.
<b>PDF 원문 인용</b>과 쪽수가 여기서 옵니다. 현재 문서 {len(pdf_docs)}종: {html.escape(', '.join(pdf_docs))}.</td></tr>
<tr><td><a href="{series.url("library")}" target="_blank" rel="noopener">AI 안전 라이브러리</a></td>
<td>법·가이드라인·정책 문서 목록. 용어 표기가 문서명에 들어간 AI 안전 문서를 카드의 <b>관련 정책 문서</b>에 4건까지 잇고
(현재 {cnt.get('linked', {}).get('with_library', 0)}개 표제어), PDF 인용 문서가 라이브러리에 있으면 출처 옆에 <b>라이브러리에서 보기</b>를 붙입니다.</td></tr>
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
    return page("소개", "about.html", body)


def rel_js():
    """docs/rel.js — 카드 안 관계도 배치(index_page 가 REL_CTX["layouts"]에 모은 것).
    window.__REL__ = {n: {id: [표제어, 영어, 색]}, t: {id: relmap.ego_layout_compact(...)}}
    마지막 줄이 페이지의 __onRel__ 을 불러, 이미 펼쳐진 카드(공유 링크로 들어온 경우)를 그린다."""
    used = {i for lay in REL_CTX["layouts"].values() for i in [lay["c"][0]] + [b[0] for b in lay["n"]]}
    names = {i: [REL_CTX["nodes"][i]["head"], REL_CTX["nodes"][i]["en"], REL_CTX["color"].get(i, "")]
             for i in sorted(used)}
    payload = json.dumps({"n": names, "t": REL_CTX["layouts"]}, ensure_ascii=False, separators=(",", ":"))
    return "window.__REL__=" + payload + ";\nif(window.__onRel__)window.__onRel__();\n"


def main():
    path = os.path.join(config.DATA, "glossary_site.json")
    if not os.path.exists(path):
        sys.exit("사이트 JSON이 없다: %s\n  python3 scripts/apply_editorial.py 를 먼저 실행하라." % path)
    data = json.load(open(path, encoding="utf-8"))
    os.makedirs(config.DOCS, exist_ok=True)
    favicon.write_files("glossary", config.DOCS)  # 탭 아이콘(PNG는 Safari용)
    for name, fn in (("index.html", index_page), ("about.html", about_page)):
        p = os.path.join(config.DOCS, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn(data))
        print("-> %s (%.1f KB)" % (p, os.path.getsize(p) / 1024))
    p = os.path.join(config.DOCS, "rel.js")
    with open(p, "w", encoding="utf-8") as f:
        f.write(rel_js())
    print("-> %s (%.1f KB, 관계도 %d)" % (p, os.path.getsize(p) / 1024, len(REL_CTX["layouts"])))
    # 옛 PDF판 경로는 통합본으로 안내
    pdf_dir = os.path.join(config.DOCS, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    redirect = chrome.redirect_html("../index.html", series.label("glossary"))
    for name in ("index.html", "about.html"):
        with open(os.path.join(pdf_dir, name), "w", encoding="utf-8") as f:
            f.write(redirect)
    with open(os.path.join(config.DOCS, ".nojekyll"), "w") as f:
        f.write("")
    stamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    print("빌드 %s · 표제어 %d" % (stamp, len(data["entries"])))


if __name__ == "__main__":
    main()
