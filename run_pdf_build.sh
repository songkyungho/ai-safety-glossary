#!/usr/bin/env bash
# PDF 원문 인용 Glossary — 코퍼스 빈도 선정 후 동향판과 병합·통합 사이트
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/extract_pdf_corpus_candidates.py
python3 scripts/extract_pdf_def_sections.py
python3 scripts/select_pdf_glossary.py
python3 scripts/pdf_localize.py
python3 scripts/merge_glossary.py
python3 scripts/build_site.py
echo "OK → docs/index.html (통합) · docs/pdf/index.html → ?src=pdf"
