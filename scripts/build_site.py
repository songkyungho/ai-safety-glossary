#!/usr/bin/env python3
"""정적 사이트 생성 — docs/index.html · docs/about.html.

지면 토큰·내비게이션은 ui_common(= AI 안전 라이브러리와 동일)에서 온다.
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
  font-size: 12px; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em; white-space: nowrap;
}
button.filter-chip {
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid var(--hairline); background: transparent;
  color: var(--text-secondary); border-radius: 999px;
  padding: 3px 10px; font: inherit; font-size: 12px; line-height: 1.35;
  cursor: pointer; white-space: nowrap;
}
button.filter-chip:hover { color: var(--ink); border-color: var(--text-muted); }
button.filter-chip .n {
  font-variant-numeric: tabular-nums; color: var(--text-muted); font-size: 11px;
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
  font-size: 12px; color: var(--text-muted); margin: 0 0 12px;
  font-variant-numeric: tabular-nums;
}
.bucket-head {
  font-size: 13px; font-weight: 700; letter-spacing: -0.02em;
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
  font-variant-numeric: tabular-nums; font-size: 12px;
  color: var(--text-muted); min-width: 2.2em;
}
.term-name {
  font-size: 18px; font-weight: 700; letter-spacing: -0.03em; color: var(--ink);
}
.term-alt {
  font-weight: 500; font-size: 14px; color: var(--text-muted);
  letter-spacing: -0.01em;
}
.term-en {
  font-size: 13px; color: var(--text-muted); letter-spacing: -0.01em;
}
.badge {
  margin-left: auto; font-size: 11px; font-weight: 600; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap;
  background: color-mix(in srgb, var(--chip) 14%, var(--surface-1));
  color: var(--chip);
  border: 1px solid color-mix(in srgb, var(--chip) 32%, var(--hairline));
}
.source-chips {
  display: flex; flex-wrap: wrap; gap: 5px; margin-left: auto;
}
.source-chip {
  font-size: 11px; font-weight: 700; border-radius: 999px;
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
  margin: 12px 0 6px; font-size: 11px; font-weight: 700;
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
  margin: 0 0 8px; font-size: 14px; line-height: 1.72;
  color: var(--ink); letter-spacing: -0.02em; font-weight: 500;
}
.quote-ko .ko-label {
  display: inline-block; margin-right: 6px;
  font-size: 10px; font-weight: 700;
  color: var(--navy);
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
.quote-text {
  margin: 0; font-size: 13px; line-height: 1.7;
  color: var(--ink-muted); letter-spacing: -0.01em;
}
.quote-cite {
  margin: 8px 0 0; font-size: 11.5px; color: var(--text-muted); line-height: 1.5;
}
.quote-cite .cite-label {
  display: inline-block; font-size: 10px; font-weight: 700;
  color: var(--navy); margin-right: 4px;
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
.quote-cite .tier-a {
  display: inline-block; font-size: 10px; font-weight: 700;
  color: var(--navy); margin-right: 4px;
}
.missing-note {
  margin: 10px 0 0; font-size: 13px; color: var(--text-muted); line-height: 1.6;
}
.bucket-badge {
  font-size: 11px; font-weight: 600; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap;
  background: color-mix(in srgb, var(--chip) 10%, var(--surface-1));
  color: var(--chip);
  border: 1px solid color-mix(in srgb, var(--chip) 26%, var(--hairline));
}
.term-metrics {
  display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 9px;
  font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums;
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
  margin-top: 7px; font-size: 11.5px; color: var(--text-muted);
  letter-spacing: -0.01em;
}
/* 설명 블록 — 참고기사 위에 한 겹 더 그은 흐린 선 안쪽에 들어간다 */
.term-def {
  margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--gridline);
}
.term-def .def-one {
  margin: 0 0 8px; font-size: 14.5px; line-height: 1.6;
  font-weight: 650; color: var(--ink); letter-spacing: -0.02em;
}
.term-def p.def-body {
  margin: 0 0 7px; font-size: 13.5px; line-height: 1.72;
  color: var(--text-secondary); letter-spacing: -0.01em;
}
.term-def p.def-body:last-of-type { margin-bottom: 0; }
.term-def .def-src {
  margin: 8px 0 0; font-size: 11.5px; color: var(--text-muted);
}
.term-def .def-src::before { content: "근거 · "; }
.term-examples {
  margin-top: 11px; padding-top: 9px; border-top: 1px solid var(--hairline);
}
.term-examples .ex-label {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em; margin: 0 0 5px;
}
.term-examples ol { margin: 0; padding-left: 0; list-style: none; }
.term-examples li {
  font-size: 13px; line-height: 1.5; margin-bottom: 3px;
  display: flex; gap: 7px; align-items: baseline;
}
.term-examples .ex-date {
  font-variant-numeric: tabular-nums; font-size: 11px; color: var(--text-muted);
  flex: 0 0 auto; min-width: 5.2em;
}
.term-examples a {
  color: var(--navy); text-decoration: underline;
  text-decoration-thickness: 1px; text-underline-offset: 2px;
}
.term-examples a:hover { color: var(--accent); }
.term-examples .ex-src { font-size: 11px; color: var(--text-muted); }

details.legend {
  margin: 0 0 16px; font-size: 13px; color: var(--text-secondary);
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 12px; padding: 10px 14px;
}
details.legend summary {
  cursor: pointer; font-size: 12px; font-weight: 700; color: var(--text-muted);
  letter-spacing: -0.02em;
}
details.legend table { border-collapse: collapse; margin-top: 10px; width: 100%; }
details.legend td { padding: 4px 8px 4px 0; vertical-align: top; line-height: 1.5; }
details.legend td:first-child {
  white-space: nowrap; font-weight: 700; color: var(--ink); font-size: 12px;
}
.empty-note {
  padding: 28px 4px; color: var(--text-muted); font-size: 14px; display: none;
}
.prose { font-size: 14.5px; line-height: 1.75; }
.prose h2 {
  font-size: 15px; margin: 26px 0 8px; letter-spacing: -0.02em;
  padding-bottom: 6px; border-bottom: 1px solid var(--gridline);
}
.prose h3 { font-size: 13.5px; margin: 18px 0 6px; color: var(--ink-muted); }
.prose table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
.prose th, .prose td {
  border-bottom: 1px solid var(--gridline); padding: 6px 8px;
  text-align: left; vertical-align: top; line-height: 1.55;
}
.prose th { color: var(--text-muted); font-size: 12px; font-weight: 700; }
.prose code {
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 5px; padding: 1px 5px; font-size: 0.88em;
}
.prose pre {
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 10px; padding: 12px 14px; overflow-x: auto; font-size: 12.5px;
}
.prose pre code { background: none; border: 0; padding: 0; }
.prose ul { padding-left: 20px; }
.prose li { margin-bottom: 4px; }
@media (max-width: 620px) {
  .source-chips { margin-left: 0; width: 100%; }
  .bucket-badge { margin-left: 0; }
  .term-examples li { flex-wrap: wrap; }
}
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
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{chrome['nav_css']}{GLOSSARY_CSS}</style>
</head>
<body>
<div class="viz-root">
{chrome['shell']}
<main class="wrap">
{body}
<footer class="site-footer">
<p>AI 안전 용어집 · 동향 코퍼스 선정·집필 정의와 PDF 원문 인용을 한자리에서 본다.
출처는 카드의 <b>동향 / PDF / 양쪽</b> 칩으로 표시한다.</p>
<p>같은 시리즈: <a href="{ui.LIBRARY_URL}" target="_blank" rel="noopener">AI 안전 라이브러리</a> ·
<a href="{ui.DIGEST_URL}" target="_blank" rel="noopener">AI 안전 동향</a></p>
</footer>
</main>
</div>
{extra_js}
</body>
</html>
"""


def def_block(d):
    """동향 편집 정의 블록."""
    if not d or not d.get("one"):
        return ""
    paras = "".join(
        '<p class="def-body">%s</p>' % html.escape(p) for p in d.get("body", [])
    )
    src = ('<p class="def-src">%s</p>' % html.escape(d["src"])) if d.get("src") else ""
    return (
        '<div class="term-def"><p class="def-one">%s</p>%s%s</div>'
        % (html.escape(d["one"]), paras, src)
    )


def pdf_quotes_html(p):
    if not p:
        return ""
    defs = p.get("definitions") or []
    if not defs:
        return '<p class="missing-note">PDF 원문 정의를 아직 확보하지 못했습니다.</p>'
    blocks = []
    for d in defs:
        page_s = d.get("pages_label") or ""
        if not page_s:
            page = d.get("pdf_page_start")
            page_end = d.get("pdf_page_end")
            if page and page_end and page != page_end:
                page_s = f"p.{page}–{page_end}"
            elif page:
                page_s = f"p.{page}"
        kind = "정의섹션" if d.get("source_kind") == "definition_section" else "본문"
        ko = ""
        if d.get("quote_ko"):
            ko = (
                f'<p class="quote-ko"><span class="ko-label">번역</span>'
                f'{html.escape(d["quote_ko"])}</p>'
            )
        title = d.get("title") or d.get("short") or ""
        blocks.append(
            f'<div class="quote-block">{ko}'
            f'<p class="quote-text">{html.escape(d.get("quote") or "")}</p>'
            f'<p class="quote-cite">'
            f'<span class="cite-label">출처</span> '
            f'{html.escape(title)}'
            f'{(" · " + html.escape(page_s)) if page_s else ""}'
            f' · {html.escape(d.get("language") or "")}'
            f" · {kind} · 원문</p></div>"
        )
    return "".join(blocks)


def source_chips_html(source):
    if source == "both":
        return (
            '<span class="source-chips">'
            '<span class="source-chip both">양쪽</span>'
            '<span class="source-chip digest">동향</span>'
            '<span class="source-chip pdf">PDF</span>'
            "</span>"
        )
    if source == "pdf":
        return '<span class="source-chips"><span class="source-chip pdf">PDF</span></span>'
    return (
        '<span class="source-chips"><span class="source-chip digest">동향</span></span>'
    )


def examples_html(d):
    if not d or not d.get("examples"):
        return ""
    ex = "".join(
        '<li><span class="ex-date">{d}</span>'
        '<span><a href="{u}" target="_blank" rel="noopener">{t}</a>'
        ' <span class="ex-src">{s}</span></span></li>'.format(
            d=html.escape((x["date"] or "")[:10]),
            u=html.escape(x["url"]),
            t=html.escape(x["title"]),
            s=html.escape(x["source"].split("·")[-1].strip()[:22]),
        )
        for x in d["examples"]
    )
    return (
        '<div class="term-examples"><p class="ex-label">참고 기사</p>'
        f"<ol>{ex}</ol></div>"
    )


def card_html(e):
    source = e.get("source") or "digest"
    d = e.get("digest")
    p = e.get("pdf")

    metrics = []
    if d:
        rec_pct = round((d.get("recency") or 0) * 100)
        gcls = "m-strong" if (d.get("gloss") or 0) >= 5 else ""
        metrics.append(
            f'<span title="동향 코퍼스 문서 수">동향 문서 <b>{d.get("df", 0)}</b></span>'
            f'<span title="등장한 서로 다른 달 수">기간 <b>{d.get("months", 0)}</b>개월</span>'
            f'<span title="최근 12개월 비중">최근 <b>{rec_pct}%</b>'
            f'<span class="rec-bar"><i style="width:{rec_pct}%"></i></span></span>'
            f'<span class="{gcls}" title="병기 문서 수">병기 <b>{d.get("gloss", 0)}</b></span>'
            f'<span title="허브 중심성">허브 <b>{(d.get("hub_norm") or 0):.2f}</b></span>'
        )
    if p:
        metrics.append(
            f'<span title="PDF 코퍼스 문서 수">PDF 문서 <b>{p.get("df", 0)}</b></span>'
            f'<span title="정의 섹션 등장">정의섹션 <b>{p.get("gloss_df", 0)}</b></span>'
            f'<span title="선정 점수">점수 <b>{p.get("score", 0)}</b></span>'
        )

    variants = ""
    if d and d.get("variants"):
        variants = (
            f'<div class="term-variants">동향 표기 · {html.escape(str(d["variants"]))}</div>'
        )
    elif p and p.get("variants"):
        vv = p["variants"]
        if isinstance(vv, list):
            vv = " · ".join(vv[:8])
        variants = f'<div class="term-variants">PDF 표기 · {html.escape(str(vv))}</div>'

    body_parts = []
    if d and d.get("one"):
        body_parts.append('<p class="section-label">이 용어집 · 집필 정의</p>')
        body_parts.append(def_block(d))
    if p:
        body_parts.append('<p class="section-label">PDF 원문 인용</p>')
        body_parts.append(pdf_quotes_html(p))
    body_parts.append(examples_html(d))

    alt = (
        ('<span class="term-alt">(%s)</span>' % html.escape(e["alt"]))
        if e.get("alt")
        else ""
    )
    q_bits = [
        e["head"],
        e.get("alt") or "",
        e["en"],
        e["bucket"],
        source,
        "동향" if source in ("digest", "both") else "",
        "pdf" if source in ("pdf", "both") else "",
    ]
    if d:
        q_bits += [d.get("one") or "", str(d.get("variants") or "")]
        q_bits += list(d.get("body") or [])
        q_bits += [x.get("title") or "" for x in d.get("examples") or []]
    if p:
        for dd in p.get("definitions") or []:
            q_bits.append(dd.get("quote") or "")
            q_bits.append(dd.get("quote_ko") or "")

    return (
        f'<article class="term-card" id="t{e["n"]}" '
        f'data-bucket="{html.escape(e["bucket_code"])}" '
        f'data-source="{html.escape(source)}" '
        f'data-n="{e["n"]}" data-df="{e.get("df", 0)}" '
        f'data-rec="{e.get("recency", 0)}" data-gloss="{e.get("gloss", 0)}" '
        f'data-hub="{e.get("hub_norm", 0)}" data-pdfdf="{e.get("pdf_df", 0)}" '
        f'data-q="{html.escape(" ".join(q_bits).lower())}" '
        f'style="--chip:{html.escape(e["color"])}">'
        f'<div class="term-head">'
        f'<span class="term-n">{e["n"]:03d}</span>'
        f'<span class="term-name">{html.escape(e["head"])}{alt}</span>'
        f'<span class="term-en">{html.escape(e["en"])}</span>'
        f'{source_chips_html(source)}'
        f'<span class="bucket-badge">{html.escape(e["bucket"])}</span>'
        f"</div>"
        f'<div class="term-metrics">{"".join(metrics)}</div>'
        f"{variants}"
        f'{"".join(body_parts)}'
        f"</article>"
    )



LEGEND = """<details class="legend" open>
<summary>출처·지표 요지</summary>
<p>표제어는 <b>동향 코퍼스</b>와 <b>PDF 리포지토리</b>에서 각각 뽑은 뒤,
영문 표기로 합쳤다. 카드 오른쪽 칩이 출처다 — <b>동향</b> · <b>PDF</b> · <b>양쪽</b>.</p>
<table>
<tr><td>동향</td><td>집필 정의 + 동향 참고 기사. 문서·기간·최근·병기·허브는 동향 코퍼스 지표.</td></tr>
<tr><td>PDF</td><td>PDF 원문 인용(+한글 대역). PDF 문서·정의섹션·점수는 Evidence Desk 지표.</td></tr>
<tr><td>양쪽</td><td>같은 개념이 두 코퍼스에 모두 오른 항. 집필 정의와 원문 인용을 병치한다.</td></tr>
</table>
</details>"""


def index_page(data):
    ents = data["entries"]
    bks = data["buckets"]
    src_meta = (data.get("meta") or {}).get("sources") or {}
    chips = "".join(
        '<button class="filter-chip" data-bucket="{c}" style="--chip:{col}">'
        '{lb} <span class="n">{n}</span></button>'.format(
            c=html.escape(b["code"]), col=html.escape(b["color"]),
            lb=html.escape(b["label"]), n=b["n"])
        for b in bks if b.get("n", 0) > 0
    )
    src_chips = "".join(
        '<button class="filter-chip" data-source="{k}">{lb} '
        '<span class="n">{n}</span></button>'.format(
            k=k, lb=html.escape(lb), n=n)
        for k, lb, n in (
            ("digest", "동향", src_meta.get("digest_only", 0) + src_meta.get("both", 0)),
            ("pdf", "PDF", src_meta.get("pdf_only", 0) + src_meta.get("both", 0)),
            ("both", "양쪽", src_meta.get("both", 0)),
            ("digest_only", "동향만", src_meta.get("digest_only", 0)),
            ("pdf_only", "PDF만", src_meta.get("pdf_only", 0)),
        )
    )
    sorts = [("bucket", "분류순"), ("df", "동향 문서"), ("pdfdf", "PDF 문서"),
             ("rec", "최근성"), ("gloss", "병기"), ("hub", "허브")]
    sort_chips = "".join(
        '<button class="filter-chip{act}" data-sort="{k}">{lb}</button>'.format(
            k=k, lb=html.escape(lb), act=" active" if k == "bucket" else "")
        for k, lb in sorts
    )
    cards = "".join(card_html(e) for e in ents)
    c = data.get("corpus") or {}
    if c.get("docs"):
        corpus_note = html.escape(
            "동향 코퍼스 {:,}건 ({} ~ {}) · 병합 {}개".format(
                c["docs"], c.get("from", ""), c.get("to", ""), len(ents)))
    else:
        corpus_note = html.escape("병합 %d개" % len(ents))
    both_n = src_meta.get("both", 0)
    body = f"""{ui.omnibox_html()}
{LEGEND}
<div id="listControls">
  <div class="filter-toolbar">
    <span class="filter-label">출처</span>
    <button class="filter-chip active" data-source="">전체 <span class="n">{len(ents)}</span></button>
    {src_chips}
  </div>
  <div class="filter-toolbar">
    <span class="filter-label">분류</span>
    <button class="filter-chip active" data-bucket="">전체 <span class="n">{len(ents)}</span></button>
    {chips}
  </div>
  <div class="filter-toolbar">
    <span class="filter-label">정렬</span>
    {sort_chips}
  </div>
</div>
<p class="result-line" id="resultLine" data-corpus="{corpus_note}">{len(ents)}개 표제어 · 양쪽 {both_n} · {corpus_note}</p>
<div id="termList">{cards}</div>
<p class="empty-note" id="emptyNote">검색 결과가 없다.</p>
"""
    js = """<script>
(function () {
  var list = document.getElementById('termList');
  var cards = Array.prototype.slice.call(list.querySelectorAll('.term-card'));
  var box = document.getElementById('omniBox');
  var line = document.getElementById('resultLine');
  var note = document.getElementById('emptyNote');
  var panel = document.getElementById('omniResults');
  if (panel) panel.remove();
  var state = { bucket: '', source: '', sort: 'bucket', q: '' };
  var total = cards.length;

  var params = new URLSearchParams(location.search);
  if (params.get('src')) state.source = params.get('src');

  var heads = {};
  cards.forEach(function (c) {
    var bc = c.dataset.bucket;
    if (!heads[bc]) {
      var badge = c.querySelector('.bucket-badge');
      heads[bc] = { label: badge ? badge.textContent : bc,
                    color: c.style.getPropertyValue('--chip') };
    }
  });

  function num(c, k) { return parseFloat(c.dataset[k]) || 0; }

  function sourceOk(c) {
    var s = c.dataset.source || '';
    if (!state.source) return true;
    if (state.source === 'digest') return s === 'digest' || s === 'both';
    if (state.source === 'pdf') return s === 'pdf' || s === 'both';
    if (state.source === 'digest_only') return s === 'digest';
    if (state.source === 'pdf_only') return s === 'pdf';
    return s === state.source;
  }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!state.bucket || c.dataset.bucket === state.bucket) &&
               sourceOk(c) &&
               (!q || c.dataset.q.indexOf(q) !== -1);
      c.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });

    var vis = cards.filter(function (c) { return !c.classList.contains('hidden'); });
    if (state.sort === 'bucket') {
      vis.sort(function (a, b) { return num(a, 'n') - num(b, 'n'); });
    } else {
      var key = state.sort === 'rec' ? 'rec' : state.sort;
      vis.sort(function (a, b) {
        var d = num(b, key) - num(a, key);
        return d !== 0 ? d : num(a, 'n') - num(b, 'n');
      });
    }

    list.querySelectorAll('.bucket-head').forEach(function (h) { h.remove(); });
    var frag = document.createDocumentFragment();
    var lastBucket = null;
    vis.forEach(function (c) {
      if (state.sort === 'bucket' && !state.bucket && c.dataset.bucket !== lastBucket) {
        lastBucket = c.dataset.bucket;
        var h = document.createElement('div');
        h.className = 'bucket-head';
        h.style.setProperty('--chip', heads[lastBucket].color);
        h.innerHTML = '<span class="bk">' + lastBucket + '.</span> ' +
                      heads[lastBucket].label;
        frag.appendChild(h);
      }
      frag.appendChild(c);
    });
    list.appendChild(frag);

    note.style.display = shown ? 'none' : 'block';
    line.textContent = shown === total
      ? total + '개 표제어 · ' + line.dataset.corpus
      : shown + ' / ' + total + '개 표시 · ' + line.dataset.corpus;

    document.querySelectorAll('button[data-source]').forEach(function (o) {
      o.classList.toggle('active', (o.dataset.source || '') === state.source);
    });
  }

  document.querySelectorAll('button[data-bucket]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.bucket = b.dataset.bucket;
      document.querySelectorAll('button[data-bucket]').forEach(function (o) {
        o.classList.toggle('active', o === b);
      });
      apply();
    });
  });
  document.querySelectorAll('button[data-source]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.source = b.dataset.source || '';
      apply();
    });
  });
  document.querySelectorAll('button[data-sort]').forEach(function (b) {
    b.addEventListener('click', function () {
      state.sort = b.dataset.sort;
      document.querySelectorAll('button[data-sort]').forEach(function (o) {
        o.classList.toggle('active', o === b);
      });
      apply();
    });
  });
  if (box) {
    box.addEventListener('input', function () { state.q = box.value; apply(); });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === '/' && ev.target.tagName !== 'INPUT') {
        ev.preventDefault(); box.focus();
      }
      if (ev.key === 'Escape') { box.value = ''; state.q = ''; apply(); box.blur(); }
    });
  }
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href^="http"]');
    if (a) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
  }, true);
  apply();
})();
</script>"""
    return page("AI 안전 용어집", "index.html", body,
                head_count=len(ents), extra_js=js)



def about_page(data):
    c = data.get("corpus") or {}
    src = (data.get("meta") or {}).get("sources") or {}
    docs = c.get("docs", 0)
    body = f"""<div class="prose">
<p>AI 안전 용어집이다. <b>동향 코퍼스</b>에서 뽑은 표제어(집필 정의·참고 기사)와
<b>PDF 리포지토리</b>에서 뽑은 표제어(원문 인용)를 영문 표기로 합쳐
한 목록으로 보여 준다. 현재 병합 <b>{src.get('merged', len(data['entries']))}개</b>
(양쪽 {src.get('both', 0)} · 동향만 {src.get('digest_only', 0)} ·
PDF만 {src.get('pdf_only', 0)}).</p>
<p>동향 코퍼스는 <a href="{ui.DIGEST_URL}" target="_blank" rel="noopener">AI 안전 동향</a>이
매일 모으는 뉴스·논문·정책문서
<b>{docs:,}건</b>({c.get('from','')} ~ {c.get('to','')})이다.</p>

<h2>두 출처를 어떻게 합쳤나</h2>
<ul>
<li>동향판·PDF판을 <b>각각</b> 기존 파이프라인으로 빌드한다.</li>
<li>영문 표기를 정규화해 조인한다. 같은 개념이면 <b>양쪽</b> 칩.</li>
<li>카드에서 집필 정의와 PDF 원문 인용은 <b>구역을 나눠</b> 병치한다.
대역(<code>quote_ko</code>)은 편집 번역이며 원문 인용이 아니다.</li>
<li>분류(버킷)는 동향판을 우선하고, PDF-only는 가까운 동향 버킷에 매핑한다.</li>
</ul>
<pre><code>run_build.sh / run_pdf_build.sh
merge_glossary.py   동향 ∪ PDF → data/glossary_merged.json
build_site.py       이 사이트</code></pre>

<h2>동향판 — 어떻게 골랐나</h2>
<p>MCP 검색만으로 뽑으면 <i>이미 아는 용어를 검색해 확인하는</i> 순환이 된다.
그래서 코퍼스에서 기계적으로 긁어 올린 뒤 사람이 선별하는 순서로 갔다.</p>
<pre><code>extract_candidates.py   제목+요약에서 한글 1~2gram·영문 1~3gram
select_top100.py        표제어 확정 + 지표 자동 결합
gloss_and_hubs.py       병기율·허브 중심성
build_json.py           표제어별 실제 용례 수집</code></pre>

<h3>분류 쿼터를 둔다</h3>
<p>점수 순으로 그냥 100개를 자르면 보도량이 많은 법제·정치 용어가 과반을
먹고 평가·정렬 기술 용어가 밀린다. 13개 분류에 쿼터를 배분했다.</p>

<h3>변이 표기의 빈도를 합산하지 않는다</h3>
<p><code>정렬</code>(260)과 <code>alignment</code>(198)를 더하면 같은 문서를 두 번
센다. 대표 표기 하나의 문서 수만 헤드라인 숫자로 쓴다.</p>

<h3>광의어를 대표로 쓰지 않는다</h3>
<p><code>안전성 평가</code>의 근거는 <code>안전성</code>(340)이 아니라
<code>안전성 평가</code>(50)다. 전자를 쓰면 표제어의 근거를 오해하게 된다.</p>

<h2>정의문을 어떻게 썼나</h2>
<p>표제어마다 <b>번역어(대안적 번역어) 원어</b> · <b>한줄 정의</b> · <b>설명 두 문단</b>을
같은 틀로 붙였다. 예컨대 <code>파인튜닝(미세조정) fine-tuning</code>처럼, 국문 표기가
둘 이상 통용되는 경우 대안역을 괄호에 넣었다 — 100개 가운데 95개가 여기 해당한다.</p>
<p>설명의 목적은 <b>한줄 정의만으로 이해가 안 되는 사람에게 개념을 풀어 주는</b>
것이다. 사전 항목처럼 깔끔하게 쓰되 친절하게 — 왜 이런 개념이 필요한지, 어떤
구조에서 그런 일이 생기는지, 무엇과 혼동되는지를 구체적인 예와 함께 짚는다.
청소 로봇이 센서를 가리는 쪽을 배우는 이야기(정렬), 존재하지 않는 인용을 형식만
완벽하게 지어내는 이야기(환각)처럼, 개념이 손에 잡히는 장면을 하나씩 붙였다.</p>
<p>두 문단은 역할을 나눈다. 첫 문단은 <b>개념의 속을 풀어 준다</b> — 왜 이런 일이
생기고 어떤 구조에서 비롯되는지. 둘째 문단은 <b>한 발 더 들어간다</b> — 인접 개념과의
구별, 실제로 어떤 모습으로 나타나는지, 왜 다루기 어려운지. 뒤쪽에 구별을 두는 이유는
이 분야에서 잘못 읽히는 대부분이 인접 개념의 혼동에서 생기기 때문이다. 해석가능성과
설명가능성, 오용과 남용, 환각과 기만, 프라이버시와 개인정보 보호, 오정보와 허위정보,
그리고 특히 <b>범용 AI 모델(GPAI)과 범용인공지능(AGI)</b>이 그렇다.</p>
<p><b>조문·표준을 특정할 수 있는 항목에는 근거를 달았다</b>(13개). EU AI법의 인간
감독·금지 관행·고위험·투명성 의무·범용 AI 모델·AI 리터러시·중대 사고 보고 조항,
GDPR과 국내 개인정보 보호법의 자동화된 결정 조항, NIST AI RMF와 ISO/IEC 42001,
성폭력처벌법과 아동·청소년성보호법, 그리고 자유권규약 제19조다. 나머지 항목의
정의문은 이 용어집을 위해 쓴 것이며 인용문이 아니다. 확인할 수 없는 수치나 날짜는
쓰지 않고 개념 설명에 머물렀다.</p>
<p>한 문단은 250자 안팎이다. 정의문은 검색 대상에 포함된다. 그래서 표제어에 없는 말로도 찾을 수 있다 —
<code>보상 해킹</code>, <code>과도 거부</code>, <code>C2PA</code>, <code>LAWS</code>,
<code>머신 언러닝</code>처럼 본문에서만 언급한 개념들이다.</p>

<h2>중심성 실험 — 무엇이 작동했나</h2>
<p>"최근성만 보지 말고 중심성도 따지자"에서 네 가지를 계산했다. 결과가 갈렸다.</p>

<h3>작동하지 않은 것 — 전부 일반어 탐지기였다</h3>
<table>
<tr><th>지표</th><th>최상위에 나온 것</th></tr>
<tr><td>degree (동시출현 이웃 수)</td><td>AI, 문제, 가능성, 있으, 에서, 등을</td></tr>
<tr><td>topic_entropy (17개 토픽 분산)</td><td>의사결정, 자원, 생태계, 등에, 있고, 통한</td></tr>
<tr><td>pagerank_pmi (PMI 가중 PageRank)</td><td>문제의식, 기여, 동기, 점이, 측면, 주로</td></tr>
</table>
<p>이유: <b>코퍼스 전체가 이미 AI 안전 문서다.</b> 그래서 그래프 중심성이 개념
위계가 아니라 국문 논문·기사의 상투적 연결어를 재발견한다. 중심성이 쓸모
있으려면 여러 도메인이 섞인 코퍼스에서 AI 안전 용어가 구별되는 군집을
이뤄야 하는데, 여기서는 그 군집이 곧 전체다.</p>
<p><code>topic_entropy</code>에 걸었던 가설("여러 영역을 관통하면 기초 개념")도
틀렸다. 코퍼스가 알려주는 건 <b>관통 = 모호함</b>이다.</p>
<p>세 지표는 <b>음의 신호로만</b> 값어치가 있다. degree가 높은데 병기율이 0에
가까우면 일반어이고(<code>위협</code> 0.79/0.03), 둘 다 높으면 핵심
기술어다(<code>정렬</code> 0.74/0.26).</p>

<h3>작동한 것 — 병기율</h3>
<p>원문이 <code>표제어(뜻풀이)</code> 형태로 쓴 비율. <b>필자가 "이건 설명이
필요하다"고 이미 판단한 흔적</b>이라, 용어집 적격성의 가장 직접적인 증거다.
이 지표가 누락 표제어 4개를 찾아냈다 — <b>사고연쇄(CoT)</b>,
<b>보정(calibration)</b>, <b>LLM 심판(LLM-as-a-Judge)</b>,
<b>작업 시간 지평</b>. <code>GPAI</code>·<code>ASR</code>·<code>XAI</code>는
기존 표제어의 원어로 확인돼 영문 표기를 보강했다.</p>
<p>괄호 내용이 실제 뜻풀이인지 검사한다. <code>첨부파일(hwp)</code>·
<code>모집(~5.30)</code> 같은 서식 괄호는 걸러낸다 — 정교화 전에는
<code>첨부파일</code>이 병기율 0.96으로 1위였다.</p>

<h2>알려진 한계</h2>
<ul>
<li><b>형태소 분석기를 쓰지 않는다.</b> 조사 제거가 휴리스틱이라 오절단이 남는다
(<code>비동의 성적</code> → <code>비동 성적</code>, 표제어에서 교정).</li>
<li><b>광의어 용례에 잡음이 있다.</b> <code>AI 감사</code>는 대표 표기가
<code>감사</code>라서 감사원 맥락까지 걸린다. 용례를 고를 때 구체적 변이를
우선하지만 완전히 걸러지지는 않는다.</li>
<li><b>정의문은 인용이 아니다.</b> 근거를 표시한 13개 항목을 뺀 나머지는 이
용어집을 위해 작성한 설명이다. 사실관계를 틀리지 않게 쓰는 데 무게를 뒀지만,
권위 있는 출처의 문구를 옮긴 것이 아니므로 인용이 필요한 자리에는 원 문헌을
확인해야 한다.</li>
<li><b>고유명사는 표제어에서 제외했다</b> (EU AI Act·NIST AI RMF·K-AISI 등).
별도 부록 대상이다.</li>
<li><b>코퍼스 요약 품질.</b> {c['docs']:,}건 중 829건은 요약이 placeholder
(<code>요약불가</code> 등)다. 용례에서는 제외한다.</li>
</ul>

<h2>소스</h2>
<p><a href="https://github.com/songkyungho/ai-safety-glossary" target="_blank"
rel="noopener">github.com/songkyungho/ai-safety-glossary</a></p>
</div>"""
    return page("소개 · AI 안전 용어집", "about.html", body)


def main():
    path = config.MERGED_JSON
    if not os.path.exists(path):
        sys.exit(
            "병합 JSON이 없다: %s\n"
            "  python3 scripts/merge_glossary.py 를 먼저 실행하라."
            % path
        )
    data = json.load(open(path, encoding="utf-8"))
    os.makedirs(config.DOCS, exist_ok=True)
    for name, fn in (("index.html", index_page), ("about.html", about_page)):
        p = os.path.join(config.DOCS, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn(data))
        print("-> %s (%.1f KB)" % (p, os.path.getsize(p) / 1024))
    # PDF 하위 경로는 통합본으로 안내
    pdf_dir = os.path.join(config.DOCS, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    redirect = """<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=../index.html?src=pdf">
<link rel="canonical" href="../index.html?src=pdf">
<title>PDF 용어집 → 통합 용어집</title>
</head><body>
<p><a href="../index.html?src=pdf">통합 용어집 (PDF 출처 보기)</a>로 이동합니다.</p>
</body></html>
"""
    with open(os.path.join(pdf_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(redirect)
    with open(os.path.join(config.DOCS, ".nojekyll"), "w") as f:
        f.write("")
    stamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    src = (data.get("meta") or {}).get("sources") or {}
    print(
        "빌드 %s · 병합 %d (양쪽 %s · 동향만 %s · PDF만 %s)"
        % (
            stamp,
            len(data["entries"]),
            src.get("both", "?"),
            src.get("digest_only", "?"),
            src.get("pdf_only", "?"),
        )
    )


if __name__ == "__main__":
    main()
