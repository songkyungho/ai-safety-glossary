#!/usr/bin/env python3
"""정의 전용 섹션(Glossary / Key Definitions / 법령 정의조 등)에서 원문 정의를 추출한다.

PDF Evidence Desk search.sqlite3 를 직결한다. MCP 검색이 아니라 heading 필터로
정의 파트만 고른다 — 본문 산문의 'X refers to' 는 여기서 다루지 않는다.

산출:
  data/pdf/def_sections_raw.json  — 채택 청크
  data/pdf/def_parsed.json        — term/quote 후보
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_config as cfg  # noqa: E402

# 권위 문서 화이트리스트. tier A = 법령·국제보고서·강령 용어집.
DOC_META: dict[str, dict[str, Any]] = {
    "doc-c4fe09068d6e": {"tier": "A", "short": "IASR 2025"},
    "doc-971d6902bec8": {"tier": "A", "short": "IASR 2026"},
    "doc-bd1392396bb5": {"tier": "A", "short": "IASR 2026 (KO)"},
    "doc-670ed9d255e5": {"tier": "A", "short": "EU GPAI CoP 안내서 (KO)"},
    "doc-f66baa3d99af": {"tier": "A", "short": "EU GPAI Guidelines Glossary"},
    "doc-6311a32b59e6": {"tier": "A", "short": "인공지능기본법", "special": "framework_act"},
    "doc-db293b2c15ea": {"tier": "A", "short": "기본법 지원데스크 사례집"},
    "doc-3801cc707813": {"tier": "B", "short": "ISO/IEC 요약 용어"},
    "doc-a666159c7715": {"tier": "B", "short": "TTA GPAI 프레임워크 부록"},
    "doc-c49c4fa002e6": {"tier": "B", "short": "안정성 확보 가이드라인"},
    "doc-bbe62cf4913a": {"tier": "B", "short": "AI 핵심용어 단면", "special": "term_book"},
    "doc-4a89863a9655": {"tier": "B", "short": "EU HLEG Trustworthy AI"},
    "doc-9c46e00f1b3f": {"tier": "B", "short": "Defining AI incidents"},
    "doc-6aab8b3b967a": {"tier": "B", "short": "OECD Defining AI incidents"},
    "doc-362c24f9cfc1": {"tier": "B", "short": "NIST AI 800-1"},
    "doc-7576edb531d9": {"tier": "B", "short": "NIST AI RMF 1.0"},
    "doc-6e73620ab6b6": {"tier": "B", "short": "NIST AI RMF GAI Profile"},
}

HEADING_OK = re.compile(
    r"(Glossary|Key Definitions|\bDefinitions\b|용어집|용어의 정의|"
    r"주요 용어|용어 정의|제2조|각종 문헌에서의 관련 용어|"
    r"① 용어 정의|용어의 뜻)",
    re.I,
)

# 하위법령집 등 타 도메인 정의 노이즈
HEADING_BLOCK = re.compile(
    r"(철도|먹는물|원자력|비행|사건부|수사|교통안전|위해요인)",
    re.I,
)

# 영문 Term: Definition (한 청크에 여러 항)
EN_TERM = re.compile(
    r"(?m)^([A-Z][A-Za-z0-9][A-Za-z0-9 \-/()'’]{0,70}?):\s+"
    r"(.+?)(?=\n[A-Z][A-Za-z0-9][A-Za-z0-9 \-/()'’]{0,70}?:|\Z)",
    re.S,
)

# GPAI 등 표: "english 한글 | 정의" 또는 "한글 | 정의"
KO_PIPE = re.compile(
    r"(?m)^(?:([A-Za-z][A-Za-z0-9 \-/()]{1,60}?)\s+)?"
    r"([가-힣A-Za-z][가-힣A-Za-z0-9 ·\-/()]{0,40}?)\s*\|\s*"
    r"(.+)$"
)

# 법령: '용어'이란 … 말한다.
LAW_DEF = re.compile(
    r"[‘']([^’']{1,40})[’']이란\s*(.+?말한다\.)",
    re.S,
)

# 핵심용어 책 heading → 표제어
TERM_BOOK_HEAD = re.compile(
    r"^(?:(?P<head>.+?)(?:이란\?|의 개념| 개요| 개념)|(?P<head2>.+?) 개요)$"
)

NOISE_LINES = re.compile(
    r"(?m)^(?:\d{1,3}|Key Definitions|Glossary|International AI Safety Report.*|"
    r"Capabilities of general-purpose AI|용어집\(Glossary\)|용어 \| 정의)\s*$"
)


def norm_key(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("–", "-").replace("—", "-").replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[()]", "", s)
    return s


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = NOISE_LINES.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def cut_quote(s: str, limit: int = 900) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= limit:
        return s
    # 법령 정의는 '말한다.' 완결을 우선
    says = list(re.finditer(r"말한다\.", s[: limit + 40]))
    if says:
        end = says[-1].end()
        if end >= limit * 0.4:
            return s[:end].strip()
    cut = s[:limit]
    for sep in (". ", "。", "다. ", "다."):
        i = cut.rfind(sep)
        if i > limit * 0.45:
            return cut[: i + len(sep)].strip()
    return cut.rsplit(" ", 1)[0].strip() + "…"


def heading_joined(path_json: str) -> str:
    try:
        path = json.loads(path_json)
    except json.JSONDecodeError:
        return path_json
    return " / ".join(path) if isinstance(path, list) else str(path)


def select_chunks(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ids = tuple(DOC_META.keys())
    qmarks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""
        SELECT c.chunk_id, c.document_id, c.text, c.heading_path_json,
               c.page_start, c.page_end,
               d.title, d.document_type, d.language, d.publication_year,
               d.current_relative_path, d.sha256
        FROM chunks c
        JOIN documents d ON d.document_id = c.document_id
        WHERE c.document_id IN ({qmarks})
        """,
        ids,
    ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        (
            chunk_id,
            document_id,
            text,
            heading_path_json,
            page_start,
            page_end,
            title,
            document_type,
            language,
            publication_year,
            rel_path,
            sha256,
        ) = r
        meta = DOC_META[document_id]
        heading = heading_joined(heading_path_json)
        special = meta.get("special")

        keep = False
        if special == "framework_act":
            keep = "제2조(정의)" in text or "제2조(정의)" in heading
        elif special == "term_book":
            keep = bool(
                re.search(r"(이란\?|개요|의 개념|개념)$", heading)
                or re.search(r"(이란\?| 개요|의 개념)", heading)
            )
        elif document_id == "doc-db293b2c15ea":
            # 기본법 제2조 해설 섹션만 (타 법령 인용 블록 제외)
            keep = (
                ("제2조" in heading and "정의" in heading)
                or heading.startswith("1. 제2")
                or ("용어 정의 및 적용 범위" in heading)
            ) and not HEADING_BLOCK.search(heading)
            if not keep and "제2조(정의)" in text and "먹는물" not in heading and "철도" not in heading:
                # 본문에 기본법 제2조가 있고 heading이 타 법령이 아닐 때만
                keep = "「" not in heading  # 타 법령 인용 heading은 「법」형태
        else:
            keep = bool(HEADING_OK.search(heading)) and not HEADING_BLOCK.search(heading)

        if not keep:
            continue

        out.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "title": title,
                "short": meta["short"],
                "tier": meta["tier"],
                "text": text,
                "heading_path": json.loads(heading_path_json),
                "heading": heading,
                "pdf_page_start": page_start,
                "pdf_page_end": page_end,
                "document_type": document_type,
                "language": language,
                "publication_year": publication_year,
                "source_relative_path": rel_path,
                "source_sha256": sha256,
            }
        )
    return out


def parse_en_colon(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    text = clean_text(chunk["text"])
    items = []
    for m in EN_TERM.finditer(text):
        term = m.group(1).strip()
        body = m.group(2).strip()
        if len(term) < 2 or len(body) < 20:
            continue
        if term.lower() in {"key definitions", "glossary", "note", "source", "figure", "table"}:
            continue
        # 페이지 숫자만인 줄 제거
        body = re.sub(r"(?m)^\d{1,3}\s*$", "", body)
        body = re.sub(r"\s+", " ", body).strip()
        items.append(_item(chunk, term, None, body, "en_colon"))
    return items


def parse_ko_pipe(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for line in chunk["text"].splitlines():
        line = line.strip()
        if "|" not in line or line.startswith("용어"):
            continue
        if line.count("|") >= 1:
            left, right = line.split("|", 1)
            left, right = left.strip(), right.strip()
            if len(left) < 2 or len(right) < 12:
                continue
            # "english 한글" 또는 "english (abbr) 한글"
            em = re.match(
                r"^([A-Za-z][A-Za-z0-9 \-/()]{1,55}?)\s+([가-힣][가-힣A-Za-z0-9 ·\-/()]{0,40})$",
                left,
            )
            if em:
                en, ko = em.group(1).strip(), em.group(2).strip()
                # 한글 쪽이 정의 조각이 아니라 번역어일 때만
                if len(ko) <= 30:
                    items.append(_item(chunk, ko, en, right, "ko_pipe"))
                continue
            # 한글만 또는 영문만
            if re.match(r"^[가-힣]", left) or re.match(r"^[A-Za-z]", left):
                # 영문 단어 뒤에 한글이 붙은 깨짐 스킵
                if re.search(r"[A-Za-z]{3,}.*[가-힣]{2,}", left) and " " in left:
                    continue
                items.append(_item(chunk, left, None, right, "ko_pipe"))
    return items


FRAMEWORK_ACT_TERMS = {
    "인공지능",
    "인공지능시스템",
    "인공지능기술",
    "고영향 인공지능",
    "인공지능사업자",
    "인공지능산업",
    "인공지능제품",
    "인공지능서비스",
    "생성형 인공지능",
}


def parse_law(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    restrict = chunk["document_id"] in {
        "doc-6311a32b59e6",
        "doc-db293b2c15ea",
        "doc-b1d553f87ab9",
    }
    text = chunk["text"]
    starts = list(re.finditer(r"[‘']([^’']{1,40})[’']이란\s*", text))
    for i, m in enumerate(starts):
        term = m.group(1).strip()
        if restrict and term not in FRAMEWORK_ACT_TERMS and not term.startswith("고영향"):
            continue
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[m.end() : end].strip()
        # 괄호 깊이 0에서 마지막 '말한다.' 까지
        depth = 0
        cut = len(body)
        for j, ch in enumerate(body):
            if ch in "(（":
                depth += 1
            elif ch in ")）":
                depth = max(0, depth - 1)
            if depth == 0 and body[j : j + 4] == "말한다":
                # '말한다.' 또는 '말한다\n'
                cut = j + 4
                if j + 4 < len(body) and body[j + 4] == ".":
                    cut = j + 5
                break
        body = re.sub(r"\s+", " ", body[:cut]).strip()
        if len(body) < 15:
            continue
        quote = f"'{term}'이란 {body}"
        items.append(_item(chunk, term, None, quote, "law_article"))
    return items


def parse_term_book(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    heading = chunk["heading"]
    if "vs" in heading.lower() or "대비" in heading or "종류" in heading:
        return []
    m = TERM_BOOK_HEAD.match(heading.strip())
    if not m:
        term = re.sub(r"(이란\?|의 개념| 개요| 개념)$", "", heading).strip()
    else:
        term = (m.group("head") or m.group("head2") or "").strip()
    if not term or len(term) < 2:
        return []
    text = clean_text(chunk["text"])
    # heading 한 번만 제거 — 표제어 본문은 유지
    if text.startswith(heading):
        text = text[len(heading) :].strip()
    elif text.startswith(term):
        # "탈옥이란? 탈옥(Jailbreak)은 …" 형태는 본문 유지
        pass
    parts = re.split(r"(?<=[.!?])\s+|(?<=다\.)\s+", text)
    body = " ".join(p for p in parts[:3] if p).strip() if parts else text
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) < 30:
        return []
    return [_item(chunk, term, None, body, "term_book")]


def _item(
    chunk: dict[str, Any],
    term: str,
    term_en: str | None,
    quote: str,
    parser: str,
) -> dict[str, Any]:
    return {
        "term": term.strip(),
        "term_en": term_en.strip() if term_en else None,
        "term_key": norm_key(term),
        "term_en_key": norm_key(term_en) if term_en else None,
        "quote": cut_quote(quote),
        "parser": parser,
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "title": chunk["title"],
        "short": chunk["short"],
        "tier": chunk["tier"],
        "heading_path": chunk["heading_path"],
        "pdf_page_start": chunk["pdf_page_start"],
        "pdf_page_end": chunk["pdf_page_end"],
        "document_type": chunk["document_type"],
        "language": chunk["language"],
        "publication_year": chunk["publication_year"],
        "source_relative_path": chunk["source_relative_path"],
        "source_sha256": chunk["source_sha256"],
    }


def parse_chunk(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    special = DOC_META[chunk["document_id"]].get("special")
    items: list[dict[str, Any]] = []
    if special == "term_book":
        items.extend(parse_term_book(chunk))
    else:
        items.extend(parse_law(chunk))
        items.extend(parse_ko_pipe(chunk))
        items.extend(parse_en_colon(chunk))
    # 중복 제거 (같은 chunk+term)
    seen = set()
    uniq = []
    for it in items:
        k = (it["chunk_id"], it["term_key"], it["quote"][:80])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    return uniq


def main() -> None:
    if not os.path.exists(cfg.EVIDENCE_DB):
        sys.exit(f"Evidence DB 없음: {cfg.EVIDENCE_DB}")

    os.makedirs(cfg.PDF_DATA, exist_ok=True)
    conn = sqlite3.connect(f"file:{cfg.EVIDENCE_DB}?mode=ro", uri=True)
    chunks = select_chunks(conn)
    conn.close()

    parsed: list[dict[str, Any]] = []
    for ch in chunks:
        parsed.extend(parse_chunk(ch))

    raw_path = cfg.SECTIONS_JSON
    parsed_path = cfg.PARSED_JSON
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "db": cfg.EVIDENCE_DB,
                "n_chunks": len(chunks),
                "chunks": chunks,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "n_items": len(parsed),
                "items": parsed,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    by_doc: dict[str, int] = {}
    for ch in chunks:
        by_doc[ch["short"]] = by_doc.get(ch["short"], 0) + 1
    print(f"정의 섹션 청크 {len(chunks)} → 파싱 항목 {len(parsed)}")
    for k, v in sorted(by_doc.items(), key=lambda x: -x[1]):
        print(f"  {v:4d}  {k}")
    print(f"wrote {raw_path}")
    print(f"wrote {parsed_path}")


if __name__ == "__main__":
    main()
