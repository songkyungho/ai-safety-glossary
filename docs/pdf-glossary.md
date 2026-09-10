# PDF 원문 인용 Glossary

동향 Glossary의 **선정 방법론**(문서빈도 신호, 토픽 쿼터, 개념어 중심)을
참고하되, **표제어 시드는 Digest Top100이 아니다.**
PDF Evidence Desk **코퍼스 전체**에서 자주 등장하는 AI 안전 용어를 뽑되,
**정의 섹션에 표제어로 있는 항을 우선**해 원문 정의를 채운다.

- **사이트:** [docs/pdf/index.html](pdf/index.html)
- **소개:** [docs/pdf/about.html](pdf/about.html)
- **데이터:** `data/pdf/glossary.json`

## 동향판과의 대응

| 단계 | 동향 Glossary | PDF 인용 Glossary |
|---|---|---|
| 후보 | Digest 제목·요약 n-gram | **전체 PDF 본문 n-gram** |
| 신호 | df · months · recency · 병기율 | df · year_span · **gloss_df** |
| 교집합 | (병기) | **정의 섹션 표제어 ∩ 코퍼스 빈도** 우선 |
| 선정 | 사람 + 버킷 쿼터 | 점수 + 버킷 쿼터 |
| 정의 | 편집부 작성 | **원문 인용** |

`gloss_df`는 동향판 **병기율**에 대응한다. 다만 표제어 풀은 정의 섹션만이
아니라 코퍼스 빈도이며, 인용 품질을 위해 정의 섹션 표제어와 겹치는 항을
먼저 채운다.

## 빌드

```bash
./run_pdf_build.sh
```

1. `extract_pdf_corpus_candidates.py` — 전체 PDF n-gram · df · gloss_df
2. `extract_pdf_def_sections.py` — Glossary / Key Definitions / 법령 제2조 등
3. `select_pdf_glossary.py` — 동의어 묶기 → 점수 → 쿼터 → 원문 매칭
4. `pdf_localize.py` — 영문 표제어 번역어 · 영문 정의 한글 대역
5. `build_pdf_site.py` — 정적 사이트

영문만 있는 표제어에는 한글 번역어를 붙이고, 영문 정의 원문 아래에
편집 대역(`quote_ko`)을 병기한다. 대역은 원문 인용이 아니다.

Evidence DB: `../pdf-evidence-desk-index/index/search.sqlite3`
(`GLOSSARY_EVIDENCE_DB` 로 덮어쓰기)

## 점수 (표제어 선정)

```
score = log1p(df) × (1 + year_span 가점) × (1 + 0.9×gloss_rate) × (1 + 청크신호) × 복합어가점
```

| 항 | 뜻 |
|---|---|
| df | 용어가 **등장한** 서로 다른 PDF 수 |
| gloss_df / gloss_rate | 정의 섹션에도 오른 문서 수 / 비율 |
| year_span | 출판연도 분산 |

정의문은 작성하지 않는다. 매칭은 정의 섹션 표제어와의 **정확 일치**를 쓴다.
