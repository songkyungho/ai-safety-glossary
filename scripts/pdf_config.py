#!/usr/bin/env python3
"""PDF 원문 인용 Glossary — 경로."""
from __future__ import annotations

import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
DATA = os.path.join(ROOT, "data")
PDF_DATA = os.path.join(DATA, "pdf")
DOCS = os.path.join(ROOT, "docs")
PDF_DOCS = os.path.join(DOCS, "pdf")

_DEFAULT_EVIDENCE_DB = os.path.normpath(
    os.path.join(
        ROOT,
        os.pardir,
        "pdf-evidence-desk-index",
        "index",
        "search.sqlite3",
    )
)
EVIDENCE_DB = os.environ.get("GLOSSARY_EVIDENCE_DB", _DEFAULT_EVIDENCE_DB)

TOP100 = os.path.join(DATA, "glossary_top100.csv")
SECTIONS_JSON = os.path.join(PDF_DATA, "def_sections_raw.json")
PARSED_JSON = os.path.join(PDF_DATA, "def_parsed.json")
SITE_JSON = os.path.join(PDF_DATA, "glossary.json")
COVERAGE_CSV = os.path.join(PDF_DATA, "coverage.csv")
