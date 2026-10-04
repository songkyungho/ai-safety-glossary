#!/usr/bin/env bash
# 용어집 공개본을 재료가 바뀐 날에만 다시 짓고 올린다. 다이제스트 일일 실행 뒤에 작업실 목록(config/daily.json)이 부른다.
#   - 재료: data/cards·scripts·번역 kit 용어·시리즈 사이트 목록. 공개본(docs/index.html)보다 새것이 없으면 아무것도 하지 않는다.
#   - 카드나 스크립트를 고치는 중(커밋 안 된 변경)이면 건너뛴다 — 쓰다 만 내용이 공개되지 않게.
#   - 카드 편집 계층과 사이트만 다시 짓는다(run_build.sh --site). 코퍼스 재추출(1~5단계)은 손으로 돌린다.
# GLOSSARY_SKIP=1 이면 건너뜀. GLOSSARY_PUBLISH=0 이면 짓기만 하고 올리지 않는다.
set -uo pipefail
cd "$(dirname "$0")/.."

if [[ "${GLOSSARY_SKIP:-0}" =~ ^(1|true|yes|on)$ ]]; then echo "용어집: GLOSSARY_SKIP — 건너뜀"; exit 0; fi
if [[ -n "$(git status --porcelain -- data/cards scripts)" ]]; then
  echo "용어집: 카드·스크립트에 커밋 안 된 변경이 있어 건너뜀"; exit 0
fi
COMMON="${AI_SAFETY_COMMON:-$HOME/Code/ai-safety-common}"
KIT="${GLOSSARY_KIT:-$HOME/Code/ai-safety-translation-kit}"
built=docs/index.html
newer=""
if [[ -f "$built" ]]; then
  newer=$(find data/cards scripts "$KIT/data/terms.json" "$COMMON/series.json" -type f \( -name '*.py' -o -name '*.json' \) -newer "$built" 2>/dev/null | head -1)
  if [[ -z "$newer" ]]; then echo "용어집: 재료 변동 없음 — 건너뜀"; exit 0; fi
fi
./run_build.sh --site >/dev/null || { echo "용어집: 빌드 실패" >&2; exit 1; }
n=$(ls data/cards/*.json | wc -l | tr -d ' ')
if [[ "${GLOSSARY_PUBLISH:-1}" =~ ^(1|true|yes|on)$ && -x "$COMMON/bin/commit_data.sh" ]]; then
  "$COMMON/bin/commit_data.sh" "$PWD" "사이트 재빌드" docs data/glossary_site.json || echo "  ⚠ 용어집: push 못 함 (다음 실행에서 다시 시도)" >&2
fi
echo "용어집: 다시 지음 (표제어 ${n})"
