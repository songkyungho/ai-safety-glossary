#!/usr/bin/env python3
"""AI 안전 용어집 Top 100 표제어 확정 — 지표는 코퍼스에서 자동 결합.

표제어 선정은 의미 판단(사람), df/months/recency는 digest.db 코퍼스에서 온다.
변이 표기(정렬/alignment)는 df를 합산하지 않고 최대 df 표기를 대표로 쓰고
변이별 df를 함께 남긴다 — 합산하면 같은 문서를 중복 계상한다.

입력: extract_candidates.py 가 만든 data/glossary_candidates.csv
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else config.CANDIDATES
OUT_CSV = config.TOP100
OUT_MD = os.path.join(config.DATA, "_top100_plain.md")

BUCKETS = [
("A. 정렬·모델 행동", [
 ("정렬","alignment",["정렬","alignment"]),
 ("오정렬","misalignment",["misalignment"]),
 ("환각","hallucination",["환각","hallucination"]),
 ("편향","bias",["편향"]),
 ("아첨 성향","sycophancy",["아첨","sycophancy"]),
 ("기만","deception",["기만","deception"]),
 ("사보타주","sabotage",["사보타주","sabotage"]),
 ("통제 상실","loss of control",["통제 상실"]),
 ("인간 감독","human oversight",["인간 감독","oversight"]),
 ("인간 피드백 기반 강화학습","RLHF",["RLHF"]),
 ("파인튜닝","fine-tuning",["파인튜닝","fine-tuning","미세조정"]),
 ("증류","distillation",["증류","distillation"]),
 ("사고연쇄","chain-of-thought (CoT)",["chain-of-thought","CoT"]),
]),
("B. 안전성 평가·측정", [
 ("안전성 평가","safety evaluation",["안전성 평가","안전 평가","안전성"]),
 ("위험 평가","risk assessment",["위험 평가","Risk Assessment"]),
 ("벤치마크","benchmark",["벤치마크"]),
 ("레드팀","red teaming",["레드팀","red-teaming"]),
 ("공격 성공률","attack success rate (ASR)",["공격 성공률","ASR"]),
 ("가드레일","guardrail",["안전장치","guardrails","guardrail"]),
 ("탈옥","jailbreak",["탈옥","jailbreak"]),
 ("프롬프트 인젝션","prompt injection",["prompt injection"]),
 ("해석가능성","interpretability",["해석가능성","interpretability"]),
 ("설명가능성","explainability (XAI)",["설명가능성","XAI"]),
 ("일반화","generalization",["일반화"]),
 ("보정","calibration",["보정","Calibration"]),
 ("LLM 심판","LLM-as-a-Judge",["LLM-as-a-Judge"]),
 ("실패 모드","failure mode",["실패 모드"]),
 ("AI 감사","AI audit",["감사","Audit"]),
]),
("C. 오용·악용 위험", [
 ("오용","misuse",["오용"]),
 ("남용","abuse",["남용"]),
 ("취약점","vulnerability",["취약점"]),
 ("위협","threat",["위협"]),
 ("사이버 공격","cyberattack",["사이버 공격"]),
 ("유해 콘텐츠","harmful content",["유해 콘텐츠"]),
 ("비동의 성적 합성물","NCII",["비동 성적"]),
 ("개인정보 침해","privacy breach",["개인정보 침해"]),
 ("검열","censorship",["검열"]),
 ("감시","surveillance",["감시","Surveillance"]),
]),
("D. 에이전트·자율성", [
 ("AI 에이전트","AI agent",["에이전트","agents","agent"]),
 ("에이전틱 AI","agentic AI",["에이전틱","agentic"]),
 ("다중 에이전트","multi-agent",["다중 에이전트","multi-agent"]),
 ("자율 에이전트","autonomous agent",["자율 에이전트","autonomous"]),
 ("자율성","autonomy",["자율성","autonomy"]),
 ("작업 시간 지평","task time horizon",["시간 지평","지평"]),
 ("도구 사용","tool use",["도구 사용"]),
 ("모델 컨텍스트 프로토콜","MCP",["MCP"]),
 ("초지능","superintelligence",["초지능"]),
 ("범용인공지능","AGI",["AGI"]),
]),
("E. 거버넌스·책임 원칙", [
 ("AI 거버넌스","AI governance",["거버넌스","Governance"]),
 ("책임성","accountability",["책임성"]),
 ("투명성","transparency",["투명성"]),
 ("공정성","fairness",["공정성"]),
 ("신뢰할 수 있는 AI","trustworthy AI",["Trustworthy"]),
 ("책임 있는 AI","responsible AI",["Responsible"]),
 ("윤리 원칙","ethical principles",["윤리","윤리 원칙","ethics"]),
 ("구속력","binding force",["구속력"]),
]),
("F. 법·규제 개념", [
 ("고위험 AI","high-risk AI",["고위험"]),
 ("생성형 AI","generative AI",["생성형","GenAI"]),
 ("범용 AI 모델","general-purpose AI model (GPAI)",["GPAI","General-Purpose"]),
 ("투명성 의무","transparency obligation",["투명성 의무"]),
 ("규정 준수","compliance",["규제 준수","규정 준수","준수"]),
 ("자동화된 의사결정","automated decision-making",["의사결정"]),
 ("개인정보 보호","data protection",["개인정보 보호","개인정보"]),
 ("프라이버시","privacy",["프라이버시"]),
 ("수출 통제","export control",["수출 통제"]),
 ("표현의 자유","freedom of expression",["표현 자유"]),
]),
("G. 표준·인증·위험관리", [
 ("위험관리","risk management",["위험 관리","위험관리","Risk Management","리스크 관리"]),
 ("위험 완화","risk mitigation",["위험 완화"]),
 ("적합성 평가","conformity assessment",["적합성 평가","적합성"]),
 ("상호운용성","interoperability",["상호운용성"]),
 ("생애주기","lifecycle",["생애주기"]),
 ("표준화","standardization",["표준화"]),
 ("인증","certification",["인증"]),
]),
("H. 보안·사이버 위협", [
 ("사이버보안","cybersecurity",["사이버보안","사이버 보안","사이버"]),
 ("사이버 방어","cyber defense",["사이버 방어"]),
 ("사이버 위협","cyber threat",["사이버 위협"]),
 ("취약점 탐지","vulnerability detection",["취약점 탐지","취약점 발견"]),
 ("격리·샌드박싱","isolation, sandboxing",["격리"]),
 ("공급망","supply chain",["공급망"]),
]),
("I. 정보생태계·합성미디어", [
 ("딥페이크","deepfake",["딥페이크","deepfake"]),
 ("허위정보","disinformation",["허위정보"]),
 ("워터마킹","watermarking",["워터마크","워터마킹"]),
 ("출처 메타데이터","provenance metadata",["메타데이터"]),
 ("AI 리터러시","AI literacy",["리터러시"]),
]),
("J. 국가안보·중대위험", [
 ("화학·생물·방사능·핵","CBRN",["CBRN"]),
 ("자율무기","autonomous weapons",["자율무기"]),
 ("국가안보","national security",["국가안보","국가 안보","National Security"]),
 ("사고 보고","incident reporting",["사고 보고","사고 대응","incident"]),
]),
("K. 이용자 보호·아동청소년·정신건강", [
 ("연령 확인","age verification",["연령 확인","연령확인","Verification"]),
 ("아동 성착취물","CSAM",["아동 성착취물","CSAM"]),
 ("아동·청소년 보호","child and youth protection",["아동 보호","청소년 보호","청소년"]),
 ("정서적 의존","emotional dependence",["정서적 의존"]),
 ("정신건강","mental health",["정신건강","정신 건강"]),
]),
("L. 기반 기술·모델 공개 방식", [
 ("대규모 언어모델","LLM",["대규모 언어모델","언어 모델","LLM"]),
 ("파운데이션 모델","foundation model",["파운데이션 모델","기반 모델"]),
 ("모델 가중치","model weights",["모델 가중치","가중치"]),
 ("학습 데이터","training data",["학습 데이터"]),
 ("오픈웨이트 모델","open-weight model",["오픈웨이트","오픈 웨이트","open-weight"]),
]),
("M. AI 주권·물리 AI", [
 ("소버린 AI","sovereign AI",["소버린","Sovereign"]),
 ("피지컬 AI","physical AI",["피지컬","Physical"]),
]),
]


def main():
    pool = {}
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        pool[r["term"].lower()] = r

    out, missing, target = [], [], 0
    for bucket, entries in BUCKETS:
        for head, en, variants in entries:
            target += 1
            found = [(v, pool[v.lower()]) for v in variants if v.lower() in pool]
            if not found:
                missing.append((bucket, head, variants))
                continue
            # variants는 구체어 우선으로 적어 뒀다 — 첫 일치를 대표로 쓴다.
            # max(df)로 잡으면 "안전성 평가"의 근거가 광의어 "안전성"(df=340)
            # 으로 부풀려져 표제어 자체의 근거를 오해하게 만든다.
            best = found[0]
            out.append({
                "bucket": bucket, "표제어": head, "영문": en,
                "대표표기": best[0], "df": int(best[1]["df"]),
                "months": int(best[1]["months"]), "recency": best[1]["recency"],
                "최대변이df": max(int(r["df"]) for _, r in found),
                "변이표기": " / ".join("%s(%s)" % (v, r["df"]) for v, r in found),
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    thin = [r for r in out if r["최대변이df"] < 15]
    lines = [
        "# AI 안전 용어집 Top 100 후보", "",
        "코퍼스: `knowledge/digest.db` 5,765건 (2009-04-13 ~ 2026-09-07)  ",
        "`df` 등장 문서 수 · `m` 등장한 달 수 · `rec` 최근 12개월 비중  ",
        "표제어는 의미 판단으로 선정, 지표는 코퍼스에서 자동 결합 (`glossary/select_top100.py`)  ",
        "고유명사(EU AI Act·NIST AI RMF·K-AISI 등)는 표제어에서 제외 — 별도 부록 대상",
        "",
        "근거가 얇은 항목(모든 변이 df<15) %d개: %s" % (
            len(thin), ", ".join(r["표제어"] for r in thin)),
    ]
    cur, i = None, 0
    for r in out:
        if r["bucket"] != cur:
            cur, i = r["bucket"], 0
            lines += ["", "## " + cur, "",
                      "| # | 표제어 | 영문 | df | m | rec | 코퍼스 표기(빈도) |",
                      "|---:|---|---|---:|---:|---:|---|"]
        i += 1
        lines.append("| %d | **%s** | %s | %d | %d | %s | %s |" % (
            i, r["표제어"], r["영문"], r["df"], r["months"],
            r["recency"], r["변이표기"]))
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print("선정 %d / 목표 %d" % (len(out), target))
    for b, h, v in missing:
        print("  !! 근거 없음: %s / %s <- %s" % (b, h, v))
    print("-> %s\n-> %s" % (OUT_CSV, OUT_MD))


if __name__ == "__main__":
    main()
