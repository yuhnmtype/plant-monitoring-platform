"""The core must stay plant-agnostic: no plant term from any profile occurs in core code or tests.

Each profile folder holds a plant_terms.txt, one term per line. A term must not occur
(case-insensitive) in any file under src/plantmon, db or tests. The terms live in the profile
folders, so this test file contains none of them.

Known limit: the match is a plain substring match, so a term also matches an unrelated word that
contains it. Pick terms that are specific enough, and report a false hit instead of dropping it.
"""

from pathlib import Path

import pytest

TERM_FILES = sorted(Path("profiles").glob("*/plant_terms.txt"))
CORE_ROOTS = [Path("src/plantmon"), Path("db"), Path("tests")]


def _core_files():
    return [
        path
        for root in CORE_ROOTS
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def test_at_least_one_terms_file_exists():
    assert TERM_FILES, "no profiles/*/plant_terms.txt: the plant-term test would check nothing"


@pytest.mark.parametrize("terms_file", TERM_FILES, ids=lambda p: p.parent.name)
def test_no_plant_term_occurs_in_core_code_or_tests(terms_file):
    terms = [t.strip().lower() for t in terms_file.read_text(encoding="utf-8").splitlines()]
    terms = [t for t in terms if t]
    assert terms, f"{terms_file} holds no term"
    hits = []
    for path in _core_files():
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        hits += [f"{path}: {term}" for term in terms if term in text]
    assert not hits, "plant terms in core files:\n" + "\n".join(hits)
