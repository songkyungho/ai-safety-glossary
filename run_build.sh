#!/usr/bin/env bash
# 용어집 전체 재빌드. 코퍼스(digest.db)는 형제 저장소 "AI Safety"에서 읽는다.
#   GLOSSARY_DIGEST_REPO=/path/to/repo ./run_build.sh  로 위치를 덮어쓸 수 있다.
# PDF판 JSON이 있으면 병합해 통합 사이트를 만든다.
set -euo pipefail
cd "$(dirname "$0")"

step() { printf '\n[%s] %s\n' "$1" "$2"; }

step 1 "후보 추출"
python3 scripts/extract_candidates.py
step 2 "표제어 확정"
python3 scripts/select_top100.py
step 3 "병기율·허브 중심성"
python3 scripts/gloss_and_hubs.py
step 4 "용례 수집 + JSON"
python3 scripts/build_json.py
step 5 "동향∪PDF 병합"
python3 scripts/merge_glossary.py
step 6 "정적 사이트"
python3 scripts/build_site.py

echo
echo "완료. docs/index.html 를 열어 확인하거나 git push 로 게시한다."
