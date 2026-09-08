#!/usr/bin/env python3
"""AI 안전 용어집 후보 추출 v2.

v1 대비 수정:
  - n-gram 인접 판정을 원문 간격(공백만 허용)으로 제한. v1은 사이에 낀
    한글/구두점을 무시해 "AI AI", "Act AI", "AI EU" 같은 허위 조합을 만들었다.
  - 용언 잔여물(밝혔다/제시한다/위해/통해...) 및 지시어 제거.
  - 요약 실패 placeholder("요약 불가", "확인 필요", "본문 내용 없음" 등) 제거.
  - 부분 n-gram 흡수: "Large Language"가 "Large Language Models"에 거의
    항상 포함되면 짧은 쪽을 버린다.
"""
from __future__ import annotations

import csv
import math
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

config.require_digest_repo()
config.add_digest_to_path()
from topic_keywords import TOPIC_KEYWORDS, match_topics  # noqa: E402

DB = config.DB
OUT = config.CANDIDATES
TODAY = date(2026, 9, 7)
RECENT_CUTOFF = (TODAY - timedelta(days=365)).isoformat()
MIN_DF = 5

PARTICLES = sorted(
    ["이라는","라는","이라고","라고","으로서","로서","으로써","로써","에서는",
     "에서도","에게는","으로는","로는","에는","에도","와는","과는","만이",
     "부터","까지","에서","에게","으로","처럼","보다","마다","조차","이며",
     "으며","하며","이나","은","는","이","가","을","를","의","에","와","과",
     "도","만","로","라","며"],
    key=len, reverse=True,
)

# 용언·부사 잔여물: 이 어미로 끝나면 명사구가 아니다.
VERB_TAIL = re.compile(
    r"(다|다고|요|죠|자|네|군|텐데|므로|면서|지만|는데|어서|아서|해야|하여|"
    r"하기|하면|한다|된다|했다|됐다|이다|있다|없다|위해|통해|대해|따라|"
    r"인해|들어|보면|하는|되는|있는|없는|같은|많은|높은|낮은|새로운|"
    r"나타났다|밝혔다|말했다|전했다|설명했다|강조했다)$"
)
DEMONSTRATIVE = re.compile(r"^(이|그|저|것|여기|거기|저기|이런|그런|저런|이러한|"
                           r"그러한|이를|이에|이로|이와|그와|다음|앞서|당시)")

# 단독(1gram)일 때만 제외 — 복합어의 머리/수식어로는 정당하다.
# ("평가"를 통째로 막으면 "위험 평가"·"안전성 평가"까지 죽는다.)
KO_SOFT = set("""
사용 평가 연구 모델 데이터 기술 위험 정책 규제 안전 보안 정보 학습 개발 성능 분석
시스템 기반 도구 환경 접근 언어 능력 행동 책임 생성 인간 통제 관리 지원 추진
계획 방안 확대 강화 마련 구축 실시 진행 개최 참여 협력 논의 검토 요구 주장
제기 언급 기준 대상 중심 역할 의미 목적 목표 산업 분야 사업 예산 투자 매출
수익 성장 확산 증가 감소 전망 기록 달성 시장 업계 온라인 미디어 콘텐츠 플랫폼
서비스 디지털 국가 국제 세계 글로벌 사회적 윤리적 지능 인공지능 정부 기업
방법 사례 전략 한계 활용 제공 발표 공개 지적 강조 설명 수준 규모 비중 결과
내용 부분 방식 과정 영향
추론 국내 해외 관련
""".split())

# 어디에 나와도 제외 — 기능어·부사·지시어.
KO_HARD = set("""
이번 지난 올해 내년 작년 최근 당시 현재 이후 이전 때문 위해 통해 대해 따라
대한 위한 우리 자신 사람 따르면 그러나 하지만 또한 특히 다만 가운데
경우 필요 가능 중요 다양 여러 다른 모든 일부 전체 각각 어떤 무엇 실제 핵심
주요 기존 함께 이날 오는 지난해 관계자 명확히 충분히 대부분 얼마나 어떻게
있는지 빠르게 이라 지속적 우선순위 불구하고 미국 한국 중국 일본 유럽 영국
독일 프랑스 서울 캘리포니아 브뤼셀 싱가포르 러시아
""".split())

EN_STOP = set("""
the a an and or but of to in on for with at by from as is are was were be been
being it its this that these those we they he she will would can could may
might should must has have had do does did not no more most new also than then
there their which who what when how all any some such other into about over
after before between during said says one two up out if so per via using use
used based including according year years week month day time first last next
own many much very well even just only now still make made get got like want
need see know think say ai its it's has been more able upon within across
""".split())

# 요약 실패/placeholder 산출물
ARTIFACT = [
    "요약불","요약 불가","확인 필요","본문 내용","제공된 정보","마감일 시행일",
    "내용 없음","정보 없음","원문 확인","링크 확인","요약 실패","본문 없음",
]

HANGUL = re.compile(r"[가-힣]+")
KO_RUN = re.compile(r"[가-힣]+")
EN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")


def strip_particle(tok):
    for p in PARTICLES:
        if tok.endswith(p) and len(tok) - len(p) >= 2:
            return tok[: -len(p)]
    return tok


def bad_ko(tok, solo):
    """solo=True면 1gram 자격, False면 복합어 구성 자격을 본다."""
    if len(tok) < 2 or tok in KO_HARD:
        return True
    if VERB_TAIL.search(tok) or DEMONSTRATIVE.match(tok):
        return True
    return solo and tok in KO_SOFT


def runs(text, pat):
    """(token, breaks_before) — 앞 토큰과 공백만으로 이어지면 breaks=False."""
    out = []
    prev_end = None
    for m in pat.finditer(text):
        gap = text[prev_end:m.start()] if prev_end is not None else None
        adjacent = gap is not None and gap != "" and gap.strip() == ""
        out.append((m.group(), adjacent))
        prev_end = m.end()
    return out


def ko_terms(text):
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


def en_terms(text):
    seq = runs(text, EN_RUN)
    out = []
    n = len(seq)
    for i in range(n):
        tk = seq[i][0]
        low = tk.lower()
        ok = (tk.isupper() and 2 <= len(tk) <= 6) or (len(low) >= 3 and low not in EN_STOP)
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


def main():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT title, summary, digest_date FROM items WHERE digest_date IS NOT NULL"
    ).fetchall()
    con.close()

    df, recent_df = Counter(), Counter()
    months = defaultdict(set)
    topic_hits = defaultdict(Counter)
    display = {}
    artifact_docs = 0

    for n, (title, summary, ddate) in enumerate(rows, 1):
        text = ((title or "") + ". " + (summary or "")).strip()
        if not text:
            continue
        if any(a in text for a in ARTIFACT):
            artifact_docs += 1
        ym = (ddate or "")[:7]
        is_recent = (ddate or "") >= RECENT_CUTOFF
        doc_topics = match_topics(text, TOPIC_KEYWORDS)
        seen = set()
        for term in ko_terms(text) + en_terms(text):
            if any(a in term for a in ARTIFACT):
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            df[key] += 1
            months[key].add(ym)
            if is_recent:
                recent_df[key] += 1
            for tp in doc_topics:
                topic_hits[key][tp] += 1
            display.setdefault(key, term)
        if n % 2000 == 0:
            print("  %d/%d" % (n, len(rows)), file=sys.stderr)

    cand = {k: v for k, v in df.items() if v >= MIN_DF}

    # 부분 n-gram 흡수: 짧은 쪽이 긴 쪽에 90% 이상 포함되면 버린다.
    drop = set()
    by_len = sorted(cand, key=lambda k: -len(k.split()))
    for long in by_len:
        parts = long.split()
        if len(parts) < 2:
            continue
        for size in range(1, len(parts)):
            for s in range(len(parts) - size + 1):
                sub = " ".join(parts[s : s + size])
                if sub in cand and sub not in drop and cand[sub] > 0:
                    if cand[long] / cand[sub] >= 0.9:
                        drop.add(sub)

    out_rows = []
    for key, d in cand.items():
        if key in drop:
            continue
        m = len(months[key])
        rec = recent_df[key] / d
        score = math.log1p(d) * math.log1p(m) * (1 + 0.8 * rec)
        tps = topic_hits[key].most_common(3)
        out_rows.append({
            "term": display[key], "df": d, "months": m,
            "recent_df": recent_df[key], "recency": round(rec, 3),
            "score": round(score, 3),
            "topic1": tps[0][0] if tps else "",
            "topic2": tps[1][0] if len(tps) > 1 else "",
            "words": len(key.split()),
            "lang": "ko" if HANGUL.search(display[key]) else "en",
        })
    out_rows.sort(key=lambda r: -r["score"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print("docs=%d  placeholder_docs=%d  candidates=%d  absorbed=%d"
          % (len(rows), artifact_docs, len(out_rows), len(drop)), file=sys.stderr)
    print("-> " + OUT, file=sys.stderr)


if __name__ == "__main__":
    main()
