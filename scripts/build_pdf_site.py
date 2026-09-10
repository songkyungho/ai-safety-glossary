#!/usr/bin/env python3
"""PDF 원문 인용 Glossary 정적 사이트 — docs/pdf/index.html · about.html.

표제어는 PDF 코퍼스 빈도로 선정하고, 정의는 원문 인용(정의 섹션 우선, 본문 보조)입니다.
"""
from __future__ import annotations

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_config as cfg  # noqa: E402
import ui_common as ui  # noqa: E402

PDF_CSS = """
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
.badge.missing {
  background: var(--surface-2); color: var(--text-muted);
  border-color: var(--hairline);
}
.missing-note {
  margin: 12px 0 0; font-size: 0.95rem; color: var(--text-muted); line-height: 1.6;
}
.term-metrics {
  display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 9px;
  font-size: 0.75rem; color: var(--text-muted); font-variant-numeric: tabular-nums;
}
.term-metrics b { color: var(--text-secondary); font-weight: 650; }
.quote-block {
  margin-top: 12px; padding: 12px 14px;
  background: var(--surface-2); border-radius: 10px;
  border: 1px solid var(--gridline);
}
.quote-block + .quote-block { margin-top: 8px; }
.quote-text {
  margin: 0; font-size: 0.95rem; line-height: 1.72;
  color: var(--ink-muted); letter-spacing: -0.01em;
}
.quote-ko {
  margin: 0 0 10px; font-size: 1rem; line-height: 1.75;
  color: var(--ink); letter-spacing: -0.02em; font-weight: 500;
}
.quote-ko .ko-label {
  display: inline-block; margin-right: 6px;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.02em;
  color: var(--navy);
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
.quote-ko.muted { font-size: 0.82rem; font-weight: 400; color: var(--text-muted); }
.quote-cite {
  margin: 8px 0 0; font-size: 0.75rem; color: var(--text-muted);
  line-height: 1.5;
}
.quote-cite .cite-label {
  display: inline-block; font-size: 0.68rem; font-weight: 700;
  color: var(--navy); margin-right: 6px;
  border: 1px solid color-mix(in srgb, var(--navy) 28%, var(--hairline));
  border-radius: 4px; padding: 1px 5px; vertical-align: 1px;
}
details.legend {
  margin: 0 0 16px; font-size: 0.95rem; color: var(--text-secondary);
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 12px; padding: 10px 14px;
}
details.legend summary {
  cursor: pointer; font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
}
details.legend p, details.legend table { margin: 8px 0 0; line-height: 1.6; }
details.legend table { border-collapse: collapse; width: 100%; font-size: 0.82rem; }
details.legend td { padding: 3px 8px 3px 0; vertical-align: top; }
details.legend td:first-child { font-weight: 700; color: var(--ink); white-space: nowrap; }
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
.prose ul, .prose ol { padding-left: 20px; }
.prose li { margin-bottom: 4px; }
.prose code {
  background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 5px; padding: 1px 5px; font-size: 0.88em;
}
.series-link {
  display: inline-block; margin-top: 6px; font-size: 0.82rem;
  color: var(--on-navy-muted);
}
.series-link a { color: var(--gold-strong); }
@media (max-width: 620px) {
  .badge { margin-left: 0; }
}
"""


def nav_html(current: str) -> str:
    items_right = [("about.html", "소개")]
    left = (
        ui._nav_item(ui.DIGEST_URL, ui.DIGEST_LABEL, active=False, rel_prefix="")
        + ui._nav_item(ui.LIBRARY_URL, ui.LIBRARY_LABEL, active=False, rel_prefix="")
        + ui._nav_item("../index.html", "AI 안전 용어집", active=True, rel_prefix="")
    )
    return (
        '<nav class="global-nav" aria-label="사이트">'
        '<div class="global-nav-inner">'
        f'<div class="global-nav-left">{left}</div>'
        f'<div class="global-nav-right">{ui._nav_items(items_right, current, rel_prefix="")}</div>'
        "</div></nav>"
    )


def shell(current: str, title: str, *, n: int) -> str:
    parts = [nav_html(current), '<header class="page-head"><div class="page-head-inner">']
    if current == "index.html":
        parts.append("<h1>AI 안전 용어집 · PDF 원문 인용</h1>")
        parts.append(
            '<p class="tagline">PDF 리포지토리에서 <strong style="color:var(--gold-strong);font-weight:650">'
            "자주 등장하는 AI 안전 용어</strong>를 뽑고, 같은 문헌의 원문 정의로 채웠습니다. "
            f'<span id="headCount">{n}</span>개.'
            f"{ui.author_byline_html()}</p>"
        )
        parts.append(
            '<p class="series-link">동향 코퍼스 기반 설명용 용어집은 '
            '<a href="../index.html">여기</a>.</p>'
        )
    else:
        parts.append(f"<h1>{html.escape(title)}</h1>")
        parts.append('<p class="tagline">PDF에서 표제어를 고르고 원문으로 채운 방법</p>')
    parts.append("</div></header>")
    return "".join(parts)


def page_wrap(current: str, title: str, body: str, data: dict, *, extra_js: str = "") -> str:
    n = data["meta"]["coverage"]["total"]
    search_docs = []
    for e in data["entries"]:
        blob = " ".join(
            [
                e["head"],
                e["en"],
                e["bucket"],
                " ".join(d.get("term_in_source") or "" for d in e["definitions"]),
                " ".join(d["quote"][:100] for d in e["definitions"]),
            ]
        )
        search_docs.append(
            {"id": f"t{e['n']}", "title": e["head"], "subtitle": e["en"], "hay": blob}
        )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{ui.NAV_CSS}
{PDF_CSS}
</style>
</head>
<body>
<div class="viz-root">
{shell(current, title, n=n)}
<main class="wrap">
{body}
</main>
{ui.footer_html()}
</div>
{ui.omnibox_boot_script(ui.safe_json({"docs": search_docs}))}
{extra_js}
</body>
</html>
"""


def render_card(e: dict) -> str:
    badge_map = {
        "multi": "복수 정의",
        "found": "원문 있음",
        "missing": "정의 미확보",
    }
    badge = badge_map.get(e["status"], e["status"])
    badge_cls = "badge missing" if e["status"] == "missing" else "badge"
    quotes = []
    for d in e["definitions"]:
        page_s = d.get("pages_label") or ""
        if not page_s:
            page = d["pdf_page_start"]
            page_s = (
                f"p.{page}"
                if page == d["pdf_page_end"] or not d["pdf_page_end"]
                else f"p.{page}–{d['pdf_page_end']}"
            )
        kind = "정의섹션" if d.get("source_kind") == "definition_section" else "본문"
        ko_block = ""
        if d.get("quote_ko"):
            ko_block = (
                f'<p class="quote-ko"><span class="ko-label">번역</span>'
                f'{html.escape(d["quote_ko"])}</p>'
            )
        elif d.get("quote_ko_missing") and not any(
            "\uac00" <= c <= "\ud7a3" for c in (d.get("quote") or "")
        ):
            ko_block = '<p class="quote-ko muted">한글 대역 미수록</p>'
        title = d.get("title") or d.get("short") or ""
        quotes.append(
            f'<div class="quote-block">'
            f'{ko_block}'
            f'<p class="quote-text">{html.escape(d["quote"])}</p>'
            f'<p class="quote-cite">'
            f'<span class="cite-label">출처</span> '
            f'{html.escape(title)} · {html.escape(page_s)}'
            f' · {html.escape(d.get("language") or "")}'
            f' · {kind}'
            f' · 원문'
            f"</p></div>"
        )
    body = (
        "".join(quotes)
        if quotes
        else '<p class="missing-note">코퍼스에 자주 등장하지만, 정의 섹션·정의형 문장에서 '
        "아직 원문을 확보하지 못했습니다.</p>"
    )
    return (
        f'<article class="term-card" id="t{e["n"]}" data-bucket="{e["bucket_code"]}" '
        f'data-status="{e["status"]}" '
        f'data-hay="{html.escape((e["head"]+" "+e["en"]+" "+(e.get("en") or "")).lower())}" '
        f'style="--chip:{e["color"]}">'
        f'<div class="term-head">'
        f'<span class="term-n">{e["n"]:02d}</span>'
        f'<span class="term-name">{html.escape(e["head"])}</span>'
        f'<span class="term-en">{html.escape(e["en"])}</span>'
        f'<span class="{badge_cls}">{badge}</span>'
        f"</div>"
        f'<div class="term-metrics">'
        f'<span>문서 <b>{e["df"]}</b></span>'
        f'<span>정의섹션 <b>{e.get("gloss_df", 0)}</b></span>'
        f'<span>점수 <b>{e["score"]}</b></span>'
        f"</div>"
        f"{body}"
        f"</article>"
    )


def index_body(data: dict) -> str:
    buckets = data["buckets"]
    n = data["meta"]["coverage"]["total"]
    chip_b = [
        f'<button type="button" class="filter-chip active" data-bucket="ALL">전체 '
        f'<span class="n">{n}</span></button>'
    ]
    for b in buckets:
        if b["n"] == 0:
            continue
        chip_b.append(
            f'<button type="button" class="filter-chip" data-bucket="{b["code"]}" '
            f'style="--chip:{b["color"]}">{html.escape(b["label"])} '
            f'<span class="n">{b["n"]}</span></button>'
        )

    cards = []
    cur_b = None
    for e in data["entries"]:
        if e["bucket_code"] != cur_b:
            cur_b = e["bucket_code"]
            cards.append(
                f'<h2 class="bucket-head" data-bucket-head="{cur_b}" '
                f'style="--chip:{e["color"]}"><span class="bk">{cur_b}</span> · '
                f'{html.escape(e["bucket"])}</h2>'
            )
        cards.append(render_card(e))

    cov = data["meta"]["coverage"]
    return f"""
<details class="legend" open>
<summary>선정·인용 요지</summary>
<p>동향 용어집의 <b>방법론</b>(문서빈도·쿼터·개념어 중심)을 참고하되,
표제어는 Digest가 아니라 <b>이 PDF 코퍼스에서 자주 등장하는 AI 안전 용어</b>입니다.
그중 <b>정의 섹션에 표제어로 오른 항</b>을 우선 선정하고, 정의문은 원문을
출처·물리 페이지와 함께 병치합니다. 영문만 있는 표제어·정의에는
<b>한글 번역어·대역</b>을 붙였습니다(대역은 편집 번역, 원문은 별도 표시).
(원문 확보 {cov.get("found", 0)} · 미확보 {cov.get("missing", 0)} · 본문 보조 {cov.get("body_fallback", 0)})</p>
<table>
<tr><td>df</td><td>용어가 등장한 서로 다른 PDF 수</td></tr>
<tr><td>정의섹션</td><td>정의 섹션에도 오른 문서 수 (gloss_df)</td></tr>
<tr><td>점수</td><td>log1p(df)×(1+연도분산)×(1+0.9×gloss_rate)×(1+청크신호)</td></tr>
</table>
</details>
{ui.omnibox_html().replace("용례", "인용문")}
<div id="listControls">
  <div class="filter-toolbar"><span class="filter-label">분류</span>{''.join(chip_b)}</div>
</div>
<p class="result-line" id="resultLine"></p>
<div id="termList">{''.join(cards)}</div>
<p class="empty-note" id="emptyNote">조건에 맞는 표제어가 없습니다.</p>
"""


def about_body(data: dict) -> str:
    meta = data["meta"]
    cov = meta["coverage"]
    rows = "".join(
        f"<tr><td>{b['code']}</td><td>{html.escape(b['label'])}</td><td>{b['n']}</td></tr>"
        for b in data["buckets"]
    )
    top = "".join(
        f"<tr><td>{e['n']}</td><td>{html.escape(e['head'])}</td>"
        f"<td>{html.escape(e['en'])}</td><td>{e['df']}</td><td>{e['score']}</td></tr>"
        for e in sorted(data["entries"], key=lambda x: -x["score"])[:15]
    )
    return f"""
<div class="prose">
<h2>동향 용어집과의 관계</h2>
<p>참고한 것은 <b>선정 방법론</b>(빈도·지속성 신호, 토픽 쿼터, 개념어 중심)입니다.
표제어 목록은 가져오지 않았고, <b>PDF 코퍼스 등장 빈도</b>로 다시 뽑았습니다.
정의는 같은 리포지토리 원문입니다.</p>

<h2>파이프라인</h2>
<ol>
<li><code>extract_pdf_corpus_candidates.py</code> — 전체 PDF n-gram · df · gloss_df</li>
<li><code>extract_pdf_def_sections.py</code> — Glossary / Key Definitions / 법령 정의조 등</li>
<li><code>select_pdf_glossary.py</code> — 점수·쿼터 선정 → 원문 정의 매칭</li>
<li><code>pdf_localize.py</code> — 영문 표제어·정의 한글화</li>
<li><code>build_pdf_site.py</code> — 이 사이트</li>
</ol>
<p>재빌드: <code>./run_pdf_build.sh</code></p>

<h2>점수</h2>
<p><code>{html.escape(meta.get("method", ""))}</code></p>
<ul>
<li><b>df</b> — 용어가 등장한 서로 다른 PDF 수</li>
<li><b>gloss_df</b> — 정의 섹션에도 오른 문서 수 (병기율 가점)</li>
<li><b>year_span</b> — 출판연도 분산</li>
<li>정의 매칭은 선정 후 단계이며, 정의 섹션 우선·본문 정의형 문장 보조</li>
<li><b>한글화</b> — 영문 표제어에 번역어, 영문 정의에 편집 대역(<code>quote_ko</code>) 병기. 원문은 유지</li>
</ul>

<h2>규모</h2>
<table>
<tr><th>코퍼스 후보</th><td>{meta.get("corpus_candidates")}</td></tr>
<tr><th>선정 표제어</th><td>{cov["total"]}</td></tr>
<tr><th>원문 확보</th><td>{cov.get("found", 0)} (복수 {cov.get("multi", 0)})</td></tr>
<tr><th>본문 보조</th><td>{cov.get("body_fallback", 0)}</td></tr>
<tr><th>정의 미확보</th><td>{cov.get("missing", 0)}</td></tr>
</table>

<h2>버킷 배분</h2>
<table>
<tr><th>코드</th><th>분류</th><th>n</th></tr>
{rows}
</table>

<h2>점수 상위 15</h2>
<table>
<tr><th>#</th><th>표제어</th><th>영문</th><th>df</th><th>score</th></tr>
{top}
</table>
</div>
"""


FILTER_JS = """
<script>
(function(){
  const cards = [...document.querySelectorAll('.term-card')];
  const heads = [...document.querySelectorAll('[data-bucket-head]')];
  const empty = document.getElementById('emptyNote');
  const line = document.getElementById('resultLine');
  let bucket = 'ALL', q = '';

  function apply() {
    let n = 0;
    const seenBucket = new Set();
    cards.forEach(c => {
      const okB = bucket === 'ALL' || c.dataset.bucket === bucket;
      const hay = (c.dataset.hay || '') + ' ' + c.textContent.toLowerCase();
      const okQ = !q || hay.includes(q);
      const show = okB && okQ;
      c.classList.toggle('hidden', !show);
      if (show) { n++; seenBucket.add(c.dataset.bucket); }
    });
    heads.forEach(h => {
      h.style.display = (bucket === 'ALL' || h.dataset.bucketHead === bucket)
        && seenBucket.has(h.dataset.bucketHead) ? '' : 'none';
    });
    if (empty) empty.style.display = n ? 'none' : 'block';
    if (line) line.textContent = n + '개 표시';
  }

  document.querySelectorAll('[data-bucket]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-bucket]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      bucket = btn.dataset.bucket;
      apply();
    });
  });
  const box = document.getElementById('omniBox');
  if (box) box.addEventListener('input', () => { q = box.value.trim().toLowerCase(); apply(); });
  apply();
})();
</script>
"""


def main() -> None:
    with open(cfg.SITE_JSON, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(cfg.PDF_DOCS, exist_ok=True)

    with open(os.path.join(cfg.PDF_DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(
            page_wrap(
                "index.html",
                "AI 안전 용어집 · PDF 원문 인용",
                index_body(data),
                data,
                extra_js=FILTER_JS,
            )
        )
    with open(os.path.join(cfg.PDF_DOCS, "about.html"), "w", encoding="utf-8") as f:
        f.write(
            page_wrap(
                "about.html",
                "소개 · PDF 원문 인용 용어집",
                about_body(data),
                data,
            )
        )
    with open(os.path.join(cfg.PDF_DOCS, "glossary.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"wrote {cfg.PDF_DOCS}/index.html ({data['meta']['coverage']})")


if __name__ == "__main__":
    main()
