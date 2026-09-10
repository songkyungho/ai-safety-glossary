#!/usr/bin/env python3
"""PDF 코퍼스 전체에서 AI 안전 용어 후보를 추출한다.

동향 Glossary extract_candidates 와 같은 취지:
  - 한글 1~2gram · 영문 1~3gram
  - df = 등장 **문서** 수 (청크 수가 아님)
  - months 대신 year_span (출판연도 분산)
  - gloss_df = 정의 섹션에도 오른 문서 수 (병기율에 대응)

입력: Evidence Desk search.sqlite3
산출: data/pdf/corpus_candidates.csv
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_config as cfg  # noqa: E402

MIN_DF = 2  # 54문서 코퍼스 — Digest(df≥5)보다 낮춤

PARTICLES = sorted(
    [
        "이라는", "라는", "이라고", "라고", "으로서", "로서", "으로써", "로써", "에서는",
        "에서도", "에게는", "으로는", "로는", "에는", "에도", "와는", "과는", "만이",
        "부터", "까지", "에서", "에게", "으로", "처럼", "보다", "마다", "조차", "이며",
        "으며", "하며", "이나", "은", "는", "이", "가", "을", "를", "의", "에", "와", "과",
        "도", "만", "로", "라", "며",
    ],
    key=len,
    reverse=True,
)

VERB_TAIL = re.compile(
    r"(다|다고|요|죠|자|네|군|텐데|므로|면서|지만|는데|어서|아서|해야|하여|"
    r"하기|하면|한다|된다|했다|됐다|이다|있다|없다|위해|통해|대해|따라|"
    r"인해|들어|보면|하는|되는|있는|없는|같은|많은|높은|낮은|새로운|"
    r"나타났다|밝혔다|말했다|전했다|설명했다|강조했다)$"
)
DEMONSTRATIVE = re.compile(
    r"^(이|그|저|것|여기|거기|저기|이런|그런|저런|이러한|그러한|이를|이에|이로|이와|그와|다음|앞서|당시)"
)

KO_SOFT = set(
    """
사용 평가 연구 모델 데이터 기술 위험 정책 규제 안전 보안 정보 학습 개발 성능 분석
시스템 기반 도구 환경 접근 방법 능력 행동 책임 생성 인간 통제 관리 지원 추진
계획 방안 확대 강화 마련 구축 실시 진행 개최 참여 협력 논의 검토 요구 주장
제기 언급 기준 대상 중심 역할 의미 목적 목표 산업 분야 사업 예산 투자
수익 성장 확산 증가 감소 전망 예측 달성 시장 업계 온라인 미디어 콘텐츠 플랫폼
서비스 디지털 국가 국제 세계 글로벌 사회적 윤리적 지능 정부 기업
방법 사례 전략 한계 활용 제공 발표 공개 지적 강조 설명 수준 규모 비중 결과
내용 부분 방식 과정 영향 추론 국내 해외 관련 그림 표 절 장 항 조
페이지 부록 참고 문헌 이상 이하 등 및 또는
""".split()
)

KO_HARD = set(
    """
이번 지난 올해 내년 작년 최근 당시 현재 이후 이전 때문 위해 통해 대해 따라
대한 위한 우리 자신 사람 따르면 그러나 하지만 또한 특히 다만 가운데
경우 필요 가능 중요 다양 여러 다른 모든 일부 전체 각각 어떤 무엇 실제 핵심
주요 기존 함께 이날 오는 지난해 관계자 명확히 충분히 대부분 얼마나 어떻게
있는지 빠르게 이라 지속적 우선순위 불구하고 미국 한국 중국 일본 유럽 영국
독일 프랑스 서울
""".split()
)

EN_STOP = set(
    """
the a an and or but of to in on for with at by from as is are was were be been
being it its this that these these those we they he she will would can could may
might should must has have had do does did not no more most new also than then
there their which who what when how all any some such other into about over
after before between during said says one two up out if so per via using use
used based including according year years week month day time first last next
own many much very well even just only now still make made get got like want
need see know think say page pages figure table section chapter appendix see
et al ibid etc above below following including within across upon under through
upon toward towards among against without while where when what who whom whose
whether whereas however therefore thus hence namely include includes
""".split()
)

# 단독 n-gram 강한 감점 (복합어는 유지)
EN_SOFT = set(
    """
human humans information development management safety process processes
intelligence government responsible responsibility framework frameworks
system systems model models risk risks data training evaluation evaluations
performance content contents control controls access support supports
policy policies regulation regulations standard standards requirement
requirements organization organisation company companies provider providers
application applications method methods approach approaches result results
impact impacts effect effects issue issues case cases level levels type types
area areas field fields paper papers study studies research report reports
technology technologies science scientific computer machine learning
artificial digital online software hardware document documents text language
word words term terms definition definitions glossary introduction conclusion
summary overview background discussion analysis recommendation recommendations
""".split()
)

# PDF 잡음
PDF_NOISE = re.compile(
    r"(법제처|국가법령정보센터|page\s*\d+|https?://|doi:|arxiv|\.pdf\b)",
    re.I,
)

HANGUL = re.compile(r"[가-힣]+")
KO_RUN = re.compile(r"[가-힣]+")
EN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")

HEADING_GLOSS = re.compile(
    r"(Glossary|Key Definitions|\bDefinitions\b|용어집|용어의 정의|"
    r"주요 용어|용어 정의|제2조|각종 문헌에서의 관련 용어)",
    re.I,
)


def strip_particle(tok: str) -> str:
    for p in PARTICLES:
        if tok.endswith(p) and len(tok) - len(p) >= 2:
            return tok[: -len(p)]
    return tok


def bad_ko(tok: str, solo: bool) -> bool:
    if len(tok) < 2 or tok in KO_HARD:
        return True
    if VERB_TAIL.search(tok) or DEMONSTRATIVE.match(tok):
        return True
    return solo and tok in KO_SOFT


def runs(text: str, pat: re.Pattern):
    out = []
    prev_end = None
    for m in pat.finditer(text):
        gap = text[prev_end : m.start()] if prev_end is not None else None
        adjacent = gap is not None and gap != "" and gap.strip() == ""
        out.append((m.group(), adjacent))
        prev_end = m.end()
    return out


def ko_terms(text: str) -> list[str]:
    seq = [(strip_particle(t), adj) for t, adj in runs(text, KO_RUN)]
    out = []
    for i, (t, _) in enumerate(seq):
        if not bad_ko(t, True):
            out.append(t)
        if i + 1 < len(seq):
            b, adj = seq[i + 1]
            if adj and not bad_ko(t, False) and not bad_ko(b, False):
                out.append(t + " " + b)
    return out


def en_terms(text: str) -> list[str]:
    seq = runs(text, EN_RUN)
    out = []
    n = len(seq)
    for i in range(n):
        tk = seq[i][0]
        low = tk.lower()
        ok = (tk.isupper() and 2 <= len(tk) <= 8) or (len(low) >= 3 and low not in EN_STOP)
        if ok:
            out.append(tk)
        for size in (2, 3):
            if i + size > n:
                break
            win = seq[i : i + size]
            if any(not adj for _, adj in win[1:]):
                break
            words = [w for w, _ in win]
            lows = [w.lower() for w in words]
            if lows[0] in EN_STOP or lows[-1] in EN_STOP:
                continue
            out.append(" ".join(words))
    return out


def heading_joined(path_json: str) -> str:
    try:
        path = json.loads(path_json)
    except json.JSONDecodeError:
        return ""
    return " / ".join(path) if isinstance(path, list) else str(path)


def main() -> None:
    if not os.path.exists(cfg.EVIDENCE_DB):
        sys.exit(f"Evidence DB 없음: {cfg.EVIDENCE_DB}")

    con = sqlite3.connect(f"file:{cfg.EVIDENCE_DB}?mode=ro", uri=True)
    rows = con.execute(
        """
        SELECT c.document_id, c.text, c.heading_path_json,
               d.publication_year, d.title, d.document_type, d.language
        FROM chunks c
        JOIN documents d ON d.document_id = c.document_id
        """
    ).fetchall()
    n_docs = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()

    df: Counter = Counter()
    gloss_df: Counter = Counter()  # 정의 섹션 문서
    years: dict[str, set] = defaultdict(set)
    chunk_hits: Counter = Counter()
    display: dict[str, str] = {}
    doc_types: dict[str, Counter] = defaultdict(Counter)

    # 문서별 등장 집합
    per_doc: dict[str, set] = defaultdict(set)
    gloss_per_doc: dict[str, set] = defaultdict(set)

    for document_id, text, heading_json, year, title, dtype, lang in rows:
        if not text or PDF_NOISE.search(text[:200] or ""):
            # 노이즈가 많아도 본문은 쓰되, 짧은 헤더만인 청크는 스킵하지 않음
            pass
        text = text or ""
        if len(text) < 40:
            continue
        heading = heading_joined(heading_json or "[]")
        in_gloss = bool(HEADING_GLOSS.search(heading))

        seen = set()
        for term in ko_terms(text) + en_terms(text):
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            per_doc[document_id].add(key)
            chunk_hits[key] += 1
            if key not in display or (term[:1].isupper() and not display[key][:1].isupper()):
                display[key] = term
            if year:
                years[key].add(int(year))
            if dtype:
                doc_types[key][dtype] += 1
            if in_gloss:
                gloss_per_doc[document_id].add(key)

    # df 집계
    for _doc, keys in per_doc.items():
        for k in keys:
            df[k] += 1
    for _doc, keys in gloss_per_doc.items():
        for k in keys:
            gloss_df[k] += 1

    # 부분 n-gram 흡수 (짧은 쪽이 긴 쪽에 거의 포함되면 감점/제거는 점수에서)
    os.makedirs(cfg.PDF_DATA, exist_ok=True)
    out_path = os.path.join(cfg.PDF_DATA, "corpus_candidates.csv")

    rows_out = []
    for key, dfi in df.items():
        if dfi < MIN_DF:
            continue
        yset = years.get(key) or set()
        year_span = (max(yset) - min(yset) + 1) if yset else 1
        gdf = gloss_df.get(key, 0)
        gloss_rate = gdf / dfi
        # Diges t식: log1p(df)×log1p(지속)×(1+가점)
        score = (
            math.log1p(dfi)
            * math.log1p(year_span)
            * (1 + 0.8 * gloss_rate)
            * (1 + 0.15 * math.log1p(chunk_hits[key]))
        )
        # 광의어 단독 감점
        solo = " " not in key and "-" not in key
        if solo and (key in KO_SOFT or key in EN_STOP or key in EN_SOFT or len(key) <= 3):
            score *= 0.2
        if key.endswith("-") or key.startswith("-"):
            continue
        rows_out.append(
            {
                "term": display.get(key, key),
                "key": key,
                "df": dfi,
                "gloss_df": gdf,
                "gloss_rate": round(gloss_rate, 3),
                "chunk_hits": chunk_hits[key],
                "year_span": year_span,
                "years": ",".join(str(y) for y in sorted(yset)),
                "score": round(score, 4),
                "lang": "KO" if HANGUL.search(display.get(key, key)) else "EN",
            }
        )

    rows_out.sort(key=lambda r: (-r["score"], -r["df"], r["key"]))
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()) if rows_out else ["term"])
        w.writeheader()
        w.writerows(rows_out)

    print(f"docs={n_docs} chunks={len(rows)} candidates={len(rows_out)} (df≥{MIN_DF})")
    print(f"wrote {out_path}")
    print("top 15:")
    for r in rows_out[:15]:
        print(
            f"  {r['score']:6.3f} df={r['df']:2d} gloss={r['gloss_df']}  {r['term']}"
        )


if __name__ == "__main__":
    main()
