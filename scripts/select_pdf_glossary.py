#!/usr/bin/env python3
"""코퍼스 빈도 후보 + 원문 정의 매칭으로 PDF Glossary를 선정한다.

1) extract_pdf_corpus_candidates.py  — 전체 PDF 등장 빈도
2) extract_pdf_def_sections.py       — 정의 섹션·본문형 정의 후보
3) 이 스크립트 — 점수·버킷 쿼터 선정 후 원문 인용 부착

동향 Glossary와 같이 df·지속성·쿼터를 쓰고, 정의 섹션 등장은 gloss_rate 가점.
정의문은 작성하지 않는다.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_config as cfg  # noqa: E402

KST = timezone(timedelta(hours=9))

AUTHORITY_RANK = {
    "law_or_regulation": 0,
    "standard": 1,
    "technical_documentation": 2,
    "international_org_report": 3,
    "policy_guidance": 4,
    "government_report": 5,
    "other": 6,
}

BUCKETS: list[tuple[str, str, str, int]] = [
    ("A", "정렬·모델 행동", "#3d3a6e", 12),
    ("B", "안전성 평가·측정", "#1d4ed8", 12),
    ("C", "오용·악용·보안", "#be123c", 10),
    ("D", "에이전트·자율성·능력", "#0369a1", 10),
    ("E", "거버넌스·원칙", "#3f5340", 8),
    ("F", "법·규제 개념", "#7c3aed", 12),
    ("G", "위험관리·표준", "#0f766e", 8),
    ("H", "정보생태계·합성미디어", "#a21caf", 8),
    ("I", "기반 기술·학습", "#475569", 10),
    ("J", "기타·횡단", "#57534e", 6),
]

BUCKET_RULES: list[tuple[str, list[str]]] = [
    ("A", [
        "align", "misalign", "hallucin", "confabul", "decept", "sycophan",
        "sabotag", "정렬", "오정렬", "환각", "기만", "아첨", "사보타주",
        "rlhf", "oversight", "감독", "schem", "goal misspec",
    ]),
    ("B", [
        "benchmark", "evaluat", "red.team", "red-team", "jailbreak", "prompt injection",
        "interpretab", "explainab", "calibrat", "audit", "탈옥", "레드팀", "벤치마크",
        "해석가능", "설명가능", "감사", "가드레일", "safeguard", "guardrail",
        "tevv", "검증", "validation", "verification",
    ]),
    ("C", [
        "misuse", "abuse", "vulnerab", "malware", "cyber", "exploit", "threat",
        "dual.use", "toxin", "cbrn", "오용", "취약", "악성", "위협", "adversarial",
        "attack", "공격", "malicious", "악용",
    ]),
    ("D", [
        "agent", "agentic", "autonom", "capability", "superintelligen",
        "agi", "loss of control", "tool use", "에이전트", "자율", "초지능",
        "통제 상실", "scaffolding", "frontier", "프론티어",
    ]),
    ("E", [
        "govern", "accountab", "transpar", "fairness", "trustworthy", "responsible",
        "ethic", "거버넌스", "책임", "투명", "공정", "윤리", "human rights",
    ]),
    ("F", [
        "고영향", "high.risk", "high-risk", "gpai", "general.purpose", "general-purpose",
        "인공지능", "생성형", "generative", "provider", "deployer", "conformity",
        "의무", "규제", "법", "systemic risk", "시스템적 위험", "고위험", "적합성",
    ]),
    ("G", [
        "risk management", "risk assessment", "risk mitigat", "lifecycle", "standard",
        "certif", "interoperab", "위험관리", "위험 평가", "생애주기", "표준", "인증",
        "상호운용", "threshold", "tolerance", "framework",
    ]),
    ("H", [
        "deepfake", "disinfo", "misinfo", "watermark", "provenance", "합성", "딥페이크",
        "허위", "워터마크", "synthetic", "fake content", "manipulat",
    ]),
    ("I", [
        "fine.tun", "distill", "train", "weight", "compute", "inference", "pretrain",
        "foundation", "llm", "neural", "deep learning", "파인튜닝", "증류",
        "학습", "가중치", "파운데이션", "open.weight", "open-weight", "parameter",
        "dataset", "데이터셋",
    ]),
]

# 표기 통합
MERGE: dict[str, str] = {
    "jailbreaking": "jailbreak",
    "jailbreaks": "jailbreak",
    "탈옥": "jailbreak",
    "misalignment": "misalignment",
    "오정렬": "misalignment",
    "alignment": "alignment",
    "align": "alignment",
    "aligned": "alignment",
    "aligning": "alignment",
    "aligns": "alignment",
    "aligning ai": "alignment",
    "정렬": "alignment",
    "ai alignment": "alignment",
    "hallucination": "hallucination",
    "hallucinations": "hallucination",
    "환각": "hallucination",
    "confabulation": "hallucination",
    "deepfake": "deepfake",
    "deepfakes": "deepfake",
    "딥페이크": "deepfake",
    "red-teaming": "red teaming",
    "red teaming": "red teaming",
    "red-team": "red teaming",
    "레드팀": "red teaming",
    "fine-tuning": "fine-tuning",
    "fine tuning": "fine-tuning",
    "finetuning": "fine-tuning",
    "미세조정": "fine-tuning",
    "파인튜닝": "fine-tuning",
    "ai agent": "ai agent",
    "ai agents": "ai agent",
    "에이전트": "ai agent",
    "prompt injection": "prompt injection",
    "프롬프트 인젝션": "prompt injection",
    "general-purpose ai": "general-purpose ai",
    "general purpose ai": "general-purpose ai",
    "gpai": "general-purpose ai",
    "범용 인공지능": "general-purpose ai",
    "범용인공지능": "general-purpose ai",
    "generative ai": "generative ai",
    "생성형 인공지능": "generative ai",
    "생성형 ai": "generative ai",
    "고영향 인공지능": "high-impact ai",
    "고위험 ai": "high-risk ai",
    "high-risk ai": "high-risk ai",
    "open-weight": "open-weight model",
    "open-weight model": "open-weight model",
    "open weight model": "open-weight model",
    "오픈웨이트": "open-weight model",
    "loss of control": "loss of control",
    "loss of control scenario": "loss of control",
    "통제 상실": "loss of control",
    "chain-of-thought": "chain-of-thought",
    "chain of thought": "chain-of-thought",
    "cot": "chain-of-thought",
    "사고연쇄": "chain-of-thought",
    "사고의 사슬": "chain-of-thought",
    "rlhf": "rlhf",
    "foundation model": "foundation model",
    "foundation models": "foundation model",
    "파운데이션 모델": "foundation model",
    "interpretability": "interpretability",
    "해석가능성": "interpretability",
    "watermarking": "watermarking",
    "워터마킹": "watermarking",
    "워터마크": "watermarking",
    "evaluation": "evaluation",
    "evaluations": "evaluation",
    "evaluate": "evaluation",
    "evaluating": "evaluation",
    "evaluated": "evaluation",
    "평가": "evaluation",
    "deception": "deception",
    "deceptive": "deception",
    "deceive": "deception",
    "기만": "deception",
    "oversight": "oversight",
    "human oversight": "human oversight",
    "인간 감독": "human oversight",
    "safeguard": "safeguards",
    "safeguards": "safeguards",
    "가드레일": "safeguards",
    "guardrail": "safeguards",
    "guardrails": "safeguards",
    "framework": "framework",
    "frameworks": "framework",
    "표준": "standards",
    "standard": "standards",
    "standards": "standards",
    "benchmark": "benchmark",
    "benchmarks": "benchmark",
    "benchmarking": "benchmark",
    "벤치마크": "benchmark",
    "audit": "audit",
    "audits": "audit",
    "감사": "audit",
    "validation": "validation",
    "validate": "validation",
    "검증": "validation",
    "explainability": "explainability",
    "explainable": "explainability",
    "설명가능": "explainability",
    "transparency": "transparency",
    "transparent": "transparency",
    "투명성": "transparency",
    "governance": "governance",
    "거버넌스": "governance",
    "capability": "capability",
    "capabilities": "capability",
    "능력": "capability",
    "misuse": "misuse",
    "오용": "misuse",
    "training": "training",
    "trained": "training",
    "train": "training",
    "학습": "training",
    "scheming": "scheming",
    "scheme": "scheming",
    "schemes": "scheming",
    "ai systems": "ai system",
    "ai system": "ai system",
    "인공지능 시스템": "ai system",
    "threat": "threat",
    "threats": "threat",
    "agent": "agent",
    "agents": "agent",
    "manipulation": "manipulation",
    "manipulate": "manipulation",
    "dataset": "dataset",
    "datasets": "dataset",
    "systemic risk": "systemic risk",
    "systemic risks": "systemic risk",
    "시스템적 위험": "systemic risk",
    "artificial intelligence": "artificial intelligence",
    "인공지능": "artificial intelligence",
    "autonomy": "autonomy",
    "autonomous": "autonomy",
    "vulnerability": "vulnerability",
    "vulnerabilities": "vulnerability",
    "malicious use": "malicious use",
    "malicious": "malicious use",
    "악용": "malicious use",
    "human in the loop": "human in the loop",
    "human-in-the-loop": "human in the loop",
    "인간 개입": "human in the loop",
    "neural network": "neural network",
    "neural networks": "neural network",
    "신경망": "neural network",
    "safety case": "safety case",
    "안전성 논증": "safety case",
    "jailbreak": "jailbreak",
    "sycophancy": "sycophancy",
    "아첨": "sycophancy",
    "goal misspecification": "goal misspecification",
    "goal misgeneralisation": "goal misgeneralisation",
    "goal misgeneralization": "goal misgeneralisation",
    "open-weight model": "open-weight model",
    "foundation model": "foundation model",
    "frontier ai": "frontier ai",
    "risk threshold": "risk threshold",
    "risk tolerance": "risk tolerance",
    "risk management": "risk management",
    "위험관리": "risk management",
    "위험 관리": "risk management",
}

HEAD_LABELS: dict[str, tuple[str, str]] = {
    "jailbreak": ("탈옥", "jailbreak"),
    "misalignment": ("오정렬", "misalignment"),
    "alignment": ("정렬", "alignment"),
    "hallucination": ("환각", "hallucination"),
    "deepfake": ("딥페이크", "deepfake"),
    "red teaming": ("레드팀", "red teaming"),
    "fine-tuning": ("파인튜닝", "fine-tuning"),
    "ai agent": ("AI 에이전트", "AI agent"),
    "prompt injection": ("프롬프트 인젝션", "prompt injection"),
    "general-purpose ai": ("범용 AI", "general-purpose AI"),
    "generative ai": ("생성형 AI", "generative AI"),
    "high-impact ai": ("고영향 인공지능", "high-impact AI"),
    "high-risk ai": ("고위험 AI", "high-risk AI"),
    "open-weight model": ("오픈웨이트 모델", "open-weight model"),
    "loss of control": ("통제 상실", "loss of control"),
    "chain-of-thought": ("사고연쇄", "chain-of-thought"),
    "rlhf": ("RLHF", "RLHF"),
    "foundation model": ("파운데이션 모델", "foundation model"),
    "interpretability": ("해석가능성", "interpretability"),
    "watermarking": ("워터마킹", "watermarking"),
    "evaluation": ("평가", "evaluation"),
    "deception": ("기만", "deception"),
    "oversight": ("감독", "oversight"),
    "human oversight": ("인간 감독", "human oversight"),
    "safeguards": ("안전장치", "safeguards"),
    "framework": ("프레임워크", "framework"),
    "standards": ("표준", "standards"),
    "benchmark": ("벤치마크", "benchmark"),
    "audit": ("감사", "audit"),
    "validation": ("검증", "validation"),
    "explainability": ("설명가능성", "explainability"),
    "transparency": ("투명성", "transparency"),
    "governance": ("거버넌스", "governance"),
    "capability": ("능력", "capability"),
    "misuse": ("오용", "misuse"),
    "training": ("학습", "training"),
    "scheming": ("scheming", "scheming"),
    "ai system": ("AI 시스템", "AI system"),
    "threat": ("위협", "threat"),
    "agent": ("에이전트", "agent"),
    "manipulation": ("조작", "manipulation"),
    "dataset": ("데이터셋", "dataset"),
    "systemic risk": ("시스템적 위험", "systemic risk"),
    "artificial intelligence": ("인공지능", "artificial intelligence"),
    "autonomy": ("자율성", "autonomy"),
    "vulnerability": ("취약점", "vulnerability"),
    "attack": ("공격", "attack"),
    "malicious use": ("악용", "malicious use"),
    "human in the loop": ("인간 개입", "human in the loop"),
    "neural network": ("신경망", "neural network"),
    "safety case": ("안전성 논증", "safety case"),
    "sycophancy": ("아첨", "sycophancy"),
    "goal misspecification": ("목표 명세 오류", "goal misspecification"),
    "goal misgeneralisation": ("목표 오일반화", "goal misgeneralisation"),
    "frontier ai": ("프론티어 AI", "frontier AI"),
    "risk threshold": ("위험 임계값", "risk threshold"),
    "risk tolerance": ("위험 허용도", "risk tolerance"),
    "risk management": ("위험관리", "risk management"),
}

# 단독으로는 표제어가 되기 어려운 일반어·기능어 (복합어는 허용)
GENERIC = {
    "model", "models", "system", "systems", "risk", "risks", "data", "ai",
    "정보", "기술", "평가", "위험", "모델", "시스템", "능력", "page", "figure",
    "table", "research", "report", "section", "chapter", "example", "examples",
    "human", "humans", "information", "development", "management", "safety",
    "under", "through", "process", "processes", "intelligence", "government",
    "responsible", "responsibility", "use", "uses", "using", "used", "user",
    "users", "work", "works", "working", "approach", "approaches", "level",
    "levels", "type", "types", "case", "cases", "issue", "issues", "area",
    "areas", "field", "fields", "paper", "papers", "study", "studies",
    "result", "results", "effect", "effects", "impact", "impacts", "context",
    "contexts", "practice", "practices", "policy", "policies", "public",
    "private", "general", "specific", "important", "different", "various",
    "related", "relevant", "potential", "possible", "available", "current",
    "future", "present", "international", "national", "global", "european",
    "while", "where", "when", "what", "who", "whom", "whose", "whether",
    "whereas", "however", "therefore", "thus", "hence", "namely", "include",
    "includes", "including", "artificial", "engaging", "cyber", "foundation",
    "generative", "real", "world", "decision", "making", "security", "rights",
    "technical", "organization", "organisation", "organizations", "organisations",
    "company", "companies", "provider", "providers", "deployer", "deployers",
    "application", "applications", "function", "functions", "activity",
    "activities", "measure", "measures", "action", "actions", "step", "steps",
    "part", "parts", "form", "forms", "way", "ways", "means", "method",
    "methods", "tool", "tools", "support", "supports",
    "access", "content", "contents", "output", "outputs", "input", "inputs",
    "value", "values", "quality", "performance", "performances", "service",
    "services", "product", "products", "market", "markets", "industry",
    "society", "social", "technical", "technology", "technologies",
    "science", "scientific", "computer", "computers",
    "digital", "online", "software", "hardware",
    "code", "codes", "document", "documents", "text", "texts", "language",
    "languages", "word", "words", "term", "terms", "definition", "definitions",
    "glossary", "introduction", "conclusion", "summary", "overview",
    "background", "discussion", "analysis", "recommendation", "recommendations",
    "requirement", "requirements", "obligation", "obligations", "right",
    "rights", "law", "laws", "regulation", "regulations", "act", "acts",
    "article", "articles", "paragraph", "annex", "appendix", "note", "notes",
    "see", "also", "etc", "including", "such", "within", "without", "among",
    "across", "between", "against", "toward", "towards", "upon", "into",
    "onto", "from", "with", "about", "above", "below", "further",
    "however", "therefore", "thus", "hence", "namely", "respectively",
    "인간", "사용", "개발", "관리", "안전", "보안", "정책", "규제", "기준",
    "대상", "수준", "결과", "내용", "방식", "과정", "영향", "관련", "경우",
    "필요", "가능", "중요", "국내", "해외", "국가", "국제", "기업", "산업",
    "often", "key", "large", "environment", "environments", "harm", "harms",
    "managing", "vulnerable", "abuse", "auditing", "auditors", "neural",
    "subject", "appropriate", "appropriately", "control", "controls",
    "deployment", "deployments",
    "adoption", "best practice", "best practices", "intended purpose",
    "validation data", "input data",
    "lifecycle stage", "model training",  # 정의 섹션 표 헤더 오탐
}


def norm(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[()\[\]{}]", " ", s)
    s = re.sub(r"[·/_]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip("-").strip()
    return s


def merge_key(term: str) -> str:
    k = norm(term)
    return MERGE.get(k, MERGE.get(k.replace(" ", ""), k))


def is_generic_key(mk: str) -> bool:
    if not mk:
        return True
    if mk in {"real world", "decision making", "decision-making"}:
        return True
    if mk in GENERIC or norm(mk) in GENERIC:
        return True
    if mk.endswith("-") or mk.startswith("-"):
        return True
    tokens = mk.split()
    if len(tokens) == 1 and tokens[0] in GENERIC:
        return True
    return False


def assign_bucket(head: str, en: str) -> str:
    blob = f"{head} {en}".lower()
    for code, kws in BUCKET_RULES:
        for kw in kws:
            if re.search(kw.replace(".", r"[\s\-]?"), blob, re.I):
                return code
    return "J"


def cut_quote(s: str, limit: int = 700) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= limit:
        return s
    says = list(re.finditer(r"말한다\.", s[: limit + 40]))
    if says and says[-1].end() >= limit * 0.4:
        return s[: says[-1].end()].strip()
    cut = s[:limit]
    for sep in (". ", "。", "다. "):
        i = cut.rfind(sep)
        if i > limit * 0.45:
            return cut[: i + len(sep)].strip()
    return cut.rsplit(" ", 1)[0].strip() + "…"


def load_corpus_candidates() -> list[dict[str, Any]]:
    path = os.path.join(cfg.PDF_DATA, "corpus_candidates.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    # merge aliases: aggregate df/gloss/score
    agg: dict[str, dict[str, Any]] = {}
    for r in rows:
        raw = (r["term"] or "").strip().rstrip("-")
        if not raw:
            continue
        mk = merge_key(raw)
        if is_generic_key(mk):
            continue
        if len(mk) < 3 and " " not in mk:
            continue
        df = int(r["df"])
        gloss = int(r["gloss_df"])
        score = float(r["score"])
        chunks = int(r["chunk_hits"])
        yspan = int(r["year_span"])
        if mk not in agg:
            if mk in HEAD_LABELS:
                head, en = HEAD_LABELS[mk]
            else:
                head, en = raw, raw
                if re.search(r"[가-힣]", raw):
                    head = raw
                if re.match(r"^[A-Za-z]", raw):
                    en = raw
            agg[mk] = {
                "key": mk,
                "head": head,
                "en": en,
                "df": df,
                "gloss_df": gloss,
                "chunk_hits": chunks,
                "year_span": yspan,
                "score": score,
                "variants": {raw},
            }
        else:
            a = agg[mk]
            a["df"] = max(a["df"], df)  # 합산 시 문서 중복 — max 사용
            a["gloss_df"] = max(a["gloss_df"], gloss)
            a["chunk_hits"] += chunks
            a["year_span"] = max(a["year_span"], yspan)
            a["score"] = max(a["score"], score)
            a["variants"].add(raw)
            if mk not in HEAD_LABELS:
                if re.search(r"[가-힣]", raw) and not re.search(r"[가-힣]", a["head"]):
                    a["head"] = raw
                if re.match(r"^[A-Za-z]", raw) and (
                    a["en"] == a["head"] or a["en"].lower() == a["key"]
                ):
                    a["en"] = raw
            else:
                a["head"], a["en"] = HEAD_LABELS[mk]

    # 재점수 (병합 후) — 복합어·정의섹션 등장 가점
    for a in agg.values():
        gloss_rate = a["gloss_df"] / max(1, a["df"])
        multi = 1.25 if " " in a["key"] or "-" in a["key"] else 1.0
        a["score"] = round(
            math.log1p(a["df"])
            * math.log1p(a["year_span"])
            * (1 + 0.9 * gloss_rate)
            * (1 + 0.12 * math.log1p(a["chunk_hits"]))
            * multi,
            4,
        )
        a["bucket_code"] = assign_bucket(a["head"], a["en"])
        a["variants"] = sorted(a["variants"])
    return list(agg.values())


def load_def_index() -> list[dict[str, Any]]:
    if not os.path.exists(cfg.PARSED_JSON):
        return []
    return json.load(open(cfg.PARSED_JSON, encoding="utf-8"))["items"]


def _keys_for(cand: dict[str, Any]) -> set[str]:
    keys = {cand["key"], norm(cand["head"]), norm(cand["en"])}
    keys |= {norm(v) for v in cand.get("variants", [])}
    keys |= {merge_key(v) for v in list(keys)}
    return {k for k in keys if k}


def def_term_matches(cand_keys: set[str], term: str, term_en: str | None) -> bool:
    """정확한 표기 일치만 허용. 단독 토큰의 구문 확장 매칭은 금지."""
    candidates = {merge_key(term), norm(term)}
    if term_en:
        candidates |= {merge_key(term_en), norm(term_en)}
    candidates.discard("")
    if candidates & cand_keys:
        return True
    # 다단어끼리만 접두 확장 허용 (예: "general purpose ai" ↔ "general purpose ai model")
    for k in cand_keys:
        if " " not in k:
            continue
        for t in candidates:
            if " " not in t:
                continue
            if t == k or t.startswith(k + " ") or k.startswith(t + " "):
                return True
    return False


def match_definitions(
    cand: dict[str, Any], def_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    keys = _keys_for(cand)
    hits = []
    seen = set()
    for it in def_items:
        if not def_term_matches(keys, it["term"], it.get("term_en")):
            continue
        rec = {
            "quote": it["quote"],
            "term_in_source": it["term"],
            "term_en_in_source": it.get("term_en"),
            "document_id": it["document_id"],
            "title": it["title"],
            "short": it["short"],
            "tier": it["tier"],
            "pdf_page_start": it["pdf_page_start"],
            "pdf_page_end": it["pdf_page_end"],
            "chunk_id": it["chunk_id"],
            "heading_path": it["heading_path"],
            "document_type": it["document_type"],
            "language": it["language"],
            "publication_year": it["publication_year"],
            "source_relative_path": it["source_relative_path"],
            "source_sha256": it.get("source_sha256"),
            "parser": it["parser"],
            "authority": it["document_type"],
            "source_kind": "definition_section",
        }
        sig = (rec["document_id"], rec["pdf_page_start"], rec["quote"][:90])
        if sig in seen:
            continue
        seen.add(sig)
        hits.append(rec)

    hits.sort(
        key=lambda d: (
            0 if d["tier"] == "A" else 1,
            AUTHORITY_RANK.get(d["authority"], 9),
            d["pdf_page_start"] or 0,
        )
    )
    return hits[:5]


def find_body_definitions(cand: dict[str, Any], limit: int = 2) -> list[dict[str, Any]]:
    """정의 섹션에 없을 때 본문에서 정의형 문장 검색.

    오인용을 막기 위해 다단어 표제어 + 강한 정의 패턴만 허용한다.
    """
    if not os.path.exists(cfg.EVIDENCE_DB):
        return []
    # 단독 일반어·짧은 토큰은 본문 보조를 쓰지 않음
    if " " not in cand["key"] and len(cand["key"]) < 10:
        return []
    terms = [cand["en"], cand["head"]] + cand.get("variants", [])[:3]
    terms = [t for t in terms if t and (" " in t or len(t) >= 10)]
    if not terms:
        return []
    con = sqlite3.connect(f"file:{cfg.EVIDENCE_DB}?mode=ro", uri=True)
    out = []
    seen = set()
    for term in terms:
        q = f'"{term}"'
        try:
            rows = con.execute(
                """
                SELECT c.chunk_id, c.document_id, c.text, c.heading_path_json,
                       c.page_start, c.page_end,
                       d.title, d.document_type, d.language, d.publication_year,
                       d.current_relative_path, d.sha256
                FROM fts_unicode f
                JOIN chunks c ON c.chunk_id = f.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                WHERE fts_unicode MATCH ?
                LIMIT 12
                """,
                (q,),
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for row in rows:
            (
                chunk_id,
                document_id,
                text,
                heading_json,
                page_start,
                page_end,
                title,
                dtype,
                language,
                year,
                rel,
                sha,
            ) = row
            if not text or term.lower() not in text.lower():
                continue
            patterns = [
                rf"(?m)^\s*{re.escape(term)}\s*[:：]\s*(.{{30,400}}?)(?:\n|\Z)",
                rf"{re.escape(term)}\s+(?:refers to|is defined as|means)\s+(.{{30,300}}?\.)",
                rf"{re.escape(term)}(?:이란|란)\s*(.{{20,300}}?(?:다\.))",
            ]
            quote = None
            for pat in patterns:
                m = re.search(pat, text, re.I | re.S)
                if m:
                    quote = cut_quote(m.group(0))
                    break
            if not quote:
                continue
            sig = (document_id, page_start, quote[:80])
            if sig in seen:
                continue
            seen.add(sig)
            try:
                heading = json.loads(heading_json)
            except json.JSONDecodeError:
                heading = []
            out.append(
                {
                    "quote": quote,
                    "term_in_source": term,
                    "term_en_in_source": None,
                    "document_id": document_id,
                    "title": title,
                    "short": title[:48],
                    "tier": "B",
                    "pdf_page_start": page_start,
                    "pdf_page_end": page_end,
                    "chunk_id": chunk_id,
                    "heading_path": heading,
                    "document_type": dtype,
                    "language": language,
                    "publication_year": year,
                    "source_relative_path": rel,
                    "source_sha256": sha,
                    "parser": "body_definitional",
                    "authority": dtype,
                    "source_kind": "body",
                }
            )
            if len(out) >= limit:
                con.close()
                return out
    con.close()
    return out


def good_def_term(term: str) -> bool:
    t = (term or "").strip()
    if len(t) < 2 or len(t) > 80:
        return False
    if t.lower().startswith(("examples of", "a situation where", "dedicated ")):
        return False
    if t.count(" ") > 8:
        return False
    # 문장형 파싱 잔여
    if re.search(r"\b(the|and|with|that|which)\b.*\b(the|and|with)\b", t, re.I) and len(t) > 50:
        return False
    return not is_generic_key(merge_key(t))


def def_keys_from_items(def_items: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for it in def_items:
        if not good_def_term(it.get("term") or ""):
            continue
        keys.add(merge_key(it["term"]))
        if it.get("term_en") and good_def_term(it["term_en"]):
            keys.add(merge_key(it["term_en"]))
    return {k for k in keys if k and not is_generic_key(k)}


def select_with_quotas(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """버킷 쿼터. 정의 섹션에 표제어가 있는 항(has_def)만 1차로 채운다."""

    def eligible(c: dict[str, Any]) -> bool:
        if is_generic_key(c["key"]):
            return False
        if c["df"] < 2:
            return False
        return True

    pool = [c for c in cands if eligible(c) and c.get("has_def")]
    # 정의 없는 고빈도 항은 잔여 슬롯용 (소수)
    pool_extra = [
        c
        for c in cands
        if eligible(c)
        and not c.get("has_def")
        and c["gloss_df"] >= 2
        and " " in c["key"]
    ]

    def sort_key(x: dict[str, Any]):
        return (-x["score"], -x["df"], -x["gloss_df"], x["head"])

    by_b: dict[str, list] = defaultdict(list)
    for c in pool:
        by_b[c["bucket_code"]].append(c)
    for code in by_b:
        by_b[code].sort(key=sort_key)

    selected = []
    used = set()
    # 1) 버킷 쿼터
    for code, _lab, _col, quota in BUCKETS:
        for c in by_b.get(code, [])[:quota]:
            used.add(c["key"])
            selected.append(c)

    # 2) 미달 버킷 보충
    for code, _lab, _col, quota in BUCKETS:
        have = sum(1 for c in selected if c["bucket_code"] == code)
        if have >= quota:
            continue
        for c in by_b.get(code, []):
            if c["key"] in used:
                continue
            selected.append(c)
            used.add(c["key"])
            have += 1
            if have >= quota or len(selected) >= 100:
                break
        if len(selected) >= 100:
            break

    # 3) 잔여 has_def
    if len(selected) < 100:
        rest = sorted(
            (c for c in pool if c["key"] not in used),
            key=sort_key,
        )
        for c in rest:
            if len(selected) >= 100:
                break
            selected.append(c)
            used.add(c["key"])

    if len(selected) < 100:
        extra = sorted(
            (c for c in pool_extra if c["key"] not in used),
            key=sort_key,
        )
        for c in extra:
            if len(selected) >= 100:
                break
            selected.append(c)
            used.add(c["key"])

    selected.sort(key=lambda x: (x["bucket_code"], -x["score"], x["head"]))
    return selected[:100]


def main() -> None:
    corpus_path = os.path.join(cfg.PDF_DATA, "corpus_candidates.csv")
    if not os.path.exists(corpus_path):
        sys.exit("먼저 extract_pdf_corpus_candidates.py 를 실행하세요.")

    cands = load_corpus_candidates()
    def_items = load_def_index()
    dkeys = def_keys_from_items(def_items)
    for c in cands:
        keys = _keys_for(c)
        c["has_def"] = bool(keys & dkeys)
    selected = select_with_quotas(cands)

    bmeta = {c: (l, col, q) for c, l, col, q in BUCKETS}
    entries = []
    n_with_def = 0
    n_body = 0
    for i, c in enumerate(selected, 1):
        defs = match_definitions(c, def_items)
        if not defs:
            defs = find_body_definitions(c, limit=2)
            if defs:
                n_body += 1
        if defs:
            n_with_def += 1
        label, color, _ = bmeta[c["bucket_code"]]
        if len(defs) >= 2:
            status = "multi"
        elif len(defs) == 1:
            status = "found"
        else:
            status = "missing"
        entries.append(
            {
                "n": i,
                "head": c["head"],
                "en": c["en"],
                "bucket_code": c["bucket_code"],
                "bucket": label,
                "color": color,
                "df": c["df"],
                "gloss_df": c["gloss_df"],
                "chunk_hits": c["chunk_hits"],
                "year_span": c["year_span"],
                "n_defs": len(defs),
                "score": c["score"],
                "status": status,
                "variants": c.get("variants", []),
                "definitions": defs,
            }
        )

    buckets = []
    for code, label, color, _q in BUCKETS:
        buckets.append(
            {
                "code": code,
                "label": label,
                "color": color,
                "n": sum(1 for e in entries if e["bucket_code"] == code),
            }
        )

    os.makedirs(cfg.PDF_DATA, exist_ok=True)
    sel_path = os.path.join(cfg.PDF_DATA, "glossary_selected.csv")
    with open(sel_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "n", "bucket_code", "head", "en", "df", "gloss_df",
                "score", "status", "n_defs",
            ],
        )
        w.writeheader()
        for e in entries:
            w.writerow(
                {
                    "n": e["n"],
                    "bucket_code": e["bucket_code"],
                    "head": e["head"],
                    "en": e["en"],
                    "df": e["df"],
                    "gloss_df": e["gloss_df"],
                    "score": e["score"],
                    "status": e["status"],
                    "n_defs": e["n_defs"],
                }
            )

    out = {
        "meta": {
            "title": "AI 안전 용어집 — PDF 원문 인용",
            "version": "3.0",
            "built_at": datetime.now(KST).isoformat(timespec="seconds"),
            "method": "corpus-frequency → score → bucket-quota → verbatim definitions",
            "inspired_by": "동향 Glossary (df·지속성·쿼터·병기율≈gloss_rate)",
            "evidence_db": cfg.EVIDENCE_DB,
            "corpus_candidates": len(cands),
            "coverage": {
                "total": len(entries),
                "found": n_with_def,
                "multi": sum(1 for e in entries if e["status"] == "multi"),
                "missing": sum(1 for e in entries if e["status"] == "missing"),
                "body_fallback": n_body,
            },
            "rules": [
                "표제어는 PDF 코퍼스 전체 등장 빈도(df)로 선정한다.",
                "다만 원문 정의가 있는 표제어(정의 섹션과 교집합)를 우선 채운다.",
                "정의 섹션 등장(gloss_df)은 병기율에 대응하는 가점이다.",
                "정의문은 작성하지 않고 정의 섹션·본문 정의형 문장을 인용한다.",
                "변이 표기 df는 합산하지 않고 max를 쓴다.",
            ],
            "score_legend": {
                "df": "용어가 등장한 서로 다른 PDF 문서 수",
                "gloss_df": "정의 섹션에도 등장한 문서 수",
                "year_span": "출판연도 분산",
                "chunk_hits": "청크 단위 등장 횟수",
            },
        },
        "buckets": buckets,
        "entries": entries,
    }
    with open(cfg.SITE_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    with open(cfg.COVERAGE_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["n", "head", "en", "bucket", "df", "gloss_df", "score", "status", "sources"]
        )
        for e in entries:
            srcs = "; ".join(
                f"{d['short']} p.{d['pdf_page_start']}" for d in e["definitions"]
            )
            w.writerow(
                [
                    e["n"],
                    e["head"],
                    e["en"],
                    e["bucket_code"],
                    e["df"],
                    e["gloss_df"],
                    e["score"],
                    e["status"],
                    srcs,
                ]
            )

    print(
        f"candidates={len(cands)} selected={len(entries)} "
        f"with_def={n_with_def} body_fallback={n_body} "
        f"missing={out['meta']['coverage']['missing']}"
    )
    for b in buckets:
        print(f"  {b['code']} {b['label']}: {b['n']}")
    print(f"wrote {cfg.SITE_JSON}")


if __name__ == "__main__":
    main()
