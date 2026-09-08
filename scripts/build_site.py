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
  .badge { margin-left: 0; }
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
<p>AI 안전 용어집 · 표제어는 <a href="{ui.DIGEST_URL}" target="_blank" rel="noopener">AI 안전 동향</a>
코퍼스에서 기계적으로 추출한 뒤 사람이 선별했다. 지표는 코퍼스에서 자동 계산된다.</p>
<p>같은 시리즈: <a href="{ui.LIBRARY_URL}" target="_blank" rel="noopener">AI 안전 라이브러리</a> ·
<a href="{ui.DIGEST_URL}" target="_blank" rel="noopener">AI 안전 동향</a></p>
</footer>
</main>
</div>
{extra_js}
</body>
</html>
"""


def def_block(e):
    """설명 블록. 정의가 아직 없으면 아무것도 그리지 않는다."""
    if not e.get("one"):
        return ""
    paras = "".join(
        '<p class="def-body">%s</p>' % html.escape(p) for p in e.get("body", [])
    )
    src = ('<p class="def-src">%s</p>' % html.escape(e["src"])) if e.get("src") else ""
    return ('<div class="term-def"><p class="def-one">%s</p>%s%s</div>'
            % (html.escape(e["one"]), paras, src))


def card_html(e):
    ex = "".join(
        '<li><span class="ex-date">{d}</span>'
        '<span><a href="{u}" target="_blank" rel="noopener">{t}</a>'
        ' <span class="ex-src">{s}</span></span></li>'.format(
            d=html.escape((x["date"] or "")[:10]),
            u=html.escape(x["url"]),
            t=html.escape(x["title"]),
            s=html.escape(x["source"].split("·")[-1].strip()[:22]),
        )
        for x in e["examples"]
    )
    rec_pct = round(e["recency"] * 100)
    return (
        '<article class="term-card" data-bucket="{bc}" data-n="{n}" '
        'data-df="{df}" data-rec="{rec}" data-gloss="{gl}" data-hub="{hub}" '
        'data-q="{q}" style="--chip:{color}">'
        '<div class="term-head">'
        '<span class="term-n">{n}</span>'
        '<span class="term-name">{head}{alt}</span>'
        '<span class="term-en">{en}</span>'
        '<span class="badge">{bucket}</span>'
        "</div>"
        '<div class="term-metrics">'
        '<span title="이 표기가 등장한 문서 수">문서 <b>{df}</b></span>'
        '<span title="등장한 서로 다른 달 수 — 반짝 용어 배제">기간 <b>{m}</b>개월</span>'
        '<span title="최근 12개월 등장 비중">최근 <b>{rec_pct}%</b>'
        '<span class="rec-bar"><i style="width:{rec_pct}%"></i></span></span>'
        '<span class="{gcls}" title="원문이 표제어(뜻풀이) 형태로 쓴 문서 수 — '
        '필자가 설명이 필요하다고 판단한 흔적">병기 <b>{gl}</b></span>'
        '<span title="원문이 한글 표제어(이 표기) 형태로 쓴 문서 수 — 원어·약어로 붙는다">'
        "괄호안 <b>{paren}</b></span>"
        '<span title="100개 표제어 내부 동시출현 그래프 중심성 (집필 설계용)">'
        "허브 <b>{hub}</b></span>"
        "</div>"
        '<div class="term-variants">코퍼스 표기 · {variants}</div>'
        "{defblock}"
        '<div class="term-examples"><p class="ex-label">참고 기사</p>'
        "<ol>{ex}</ol></div>"
        "</article>"
    ).format(
        bc=html.escape(e["bucket_code"]),
        n=e["n"],
        df=e["df"],
        m=e["months"],
        rec=e["recency"],
        rec_pct=rec_pct,
        gl=e["gloss"],
        gcls="m-strong" if e["gloss"] >= 5 else "",
        paren=e["paren"],
        hub=("%.2f" % e["hub_norm"]),
        color=html.escape(e["color"]),
        head=html.escape(e["head"]),
        alt=('<span class="term-alt">(%s)</span>' % html.escape(e["alt"]))
        if e.get("alt") else "",
        defblock=def_block(e),
        en=html.escape(e["en"]),
        bucket=html.escape(e["bucket"]),
        variants=html.escape(e["variants"]),
        q=html.escape(
            " ".join(
                [e["head"], e.get("alt", ""), e["en"], e["bucket"],
                 e["variants"], e.get("one", "")]
                + list(e.get("body", []))
                + [x["title"] for x in e["examples"]]
            ).lower()
        ),
        ex=ex,
    )


LEGEND = """<details class="legend">
<summary>지표 읽는 법 — 열기</summary>
<table>
<tr><td>문서</td><td>그 표기가 등장한 <b>문서 수</b>. 원시 빈도가 아니다 —
한 사안이 여러 매체에 실려도 그만큼 부풀지 않게 문서 단위로 센다.</td></tr>
<tr><td>기간</td><td>등장한 서로 다른 달 수. 한 달에 몰려 나온 반짝 용어를 걸러낸다.</td></tr>
<tr><td>최근</td><td>최근 12개월 등장 비중. 100%에 가까우면 신생 용어다
(<b>증류</b>·<b>레드팀</b>·<b>보정</b>이 그렇다).</td></tr>
<tr><td>병기</td><td>원문이 <code>표제어(뜻풀이)</code> 형태로 쓴 문서 수.
<b>필자가 "이건 설명이 필요하다"고 이미 판단한 흔적</b>이라, 용어집 적격성의
가장 직접적인 증거다. <b>정렬</b>은 260건 중 78건에서 병기된다.</td></tr>
<tr><td>괄호안</td><td>원문이 <code>한글 표제어(이 표기)</code> 형태로 쓴 문서 수.
이 표기가 원어·약어로 붙는다는 뜻이다 (GPAI·ASR·CoT·XAI).</td></tr>
<tr><td>허브</td><td>100개 표제어끼리의 동시출현 그래프 중심성.
<b>선정용이 아니라 집필 설계용</b>이다 — 값이 낮은 건 "덜 중요하다"가 아니라
"별개 영역이다"를 뜻한다(피지컬 AI·소버린 AI).</td></tr>
</table>
</details>"""


def index_page(data):
    ents = data["entries"]
    bks = data["buckets"]
    chips = "".join(
        '<button class="filter-chip" data-bucket="{c}" style="--chip:{col}">'
        "{lb} <span class=\"n\">{n}</span></button>".format(
            c=html.escape(b["code"]), col=html.escape(b["color"]),
            lb=html.escape(b["label"]), n=b["n"])
        for b in bks
    )
    sorts = [("bucket", "분류순"), ("df", "문서 수"), ("rec", "최근성"),
             ("gloss", "병기"), ("hub", "허브")]
    sort_chips = "".join(
        '<button class="filter-chip{act}" data-sort="{k}">{lb}</button>'.format(
            k=k, lb=html.escape(lb), act=" active" if k == "bucket" else "")
        for k, lb in sorts
    )
    cards = "".join(card_html(e) for e in ents)
    c = data["corpus"]
    corpus_note = html.escape(
        "코퍼스 {:,}건 ({} ~ {})".format(c["docs"], c["from"], c["to"]))
    body = f"""{ui.omnibox_html()}
{LEGEND}
<div id="listControls">
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
<p class="result-line" id="resultLine" data-corpus="{corpus_note}">{len(ents)}개 표제어 · {corpus_note}</p>
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
  var state = { bucket: '', sort: 'bucket', q: '' };
  var total = cards.length;

  var heads = {};
  cards.forEach(function (c) {
    var bc = c.dataset.bucket;
    if (!heads[bc]) {
      var badge = c.querySelector('.badge');
      heads[bc] = { label: badge ? badge.textContent : bc,
                    color: c.style.getPropertyValue('--chip') };
    }
  });

  function num(c, k) { return parseFloat(c.dataset[k]) || 0; }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!state.bucket || c.dataset.bucket === state.bucket) &&
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
  }

  document.querySelectorAll('[data-bucket]').forEach(function (b) {
    if (b.tagName !== 'BUTTON') return;
    b.addEventListener('click', function () {
      state.bucket = b.dataset.bucket;
      document.querySelectorAll('button[data-bucket]').forEach(function (o) {
        o.classList.toggle('active', o === b);
      });
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
    c = data["corpus"]
    body = f"""<div class="prose">
<p>AI 안전 동향 코퍼스에서 용어집으로 만들 값어치가 있는 표제어
<b>100개</b>를 뽑았다. 코퍼스는 <a href="{ui.DIGEST_URL}" target="_blank"
rel="noopener">AI 안전 동향</a>이 매일 모으는 뉴스·논문·정책문서
<b>{c['docs']:,}건</b>({c['from']} ~ {c['to']})이다.</p>

<h2>어떻게 골랐나</h2>
<p>MCP 검색만으로 뽑으면 <i>이미 아는 용어를 검색해 확인하는</i> 순환이 된다.
그래서 코퍼스에서 기계적으로 긁어 올린 뒤 사람이 선별하는 순서로 갔다.</p>
<pre><code>extract_candidates.py   제목+요약에서 한글 1~2gram·영문 1~3gram → 후보 10,435개
select_top100.py        표제어 확정 (의미 판단) + 지표 자동 결합
gloss_and_hubs.py       병기율·허브 중심성
build_json.py           표제어별 실제 용례 수집
build_site.py           이 사이트</code></pre>

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
    data = json.load(open(config.SITE_JSON, encoding="utf-8"))
    os.makedirs(config.DOCS, exist_ok=True)
    for name, fn in (("index.html", index_page), ("about.html", about_page)):
        p = os.path.join(config.DOCS, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn(data))
        print("-> %s (%.1f KB)" % (p, os.path.getsize(p) / 1024))
    with open(os.path.join(config.DOCS, ".nojekyll"), "w") as f:
        f.write("")
    stamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    print("빌드 %s · 표제어 %d개" % (stamp, len(data["entries"])))


if __name__ == "__main__":
    main()
