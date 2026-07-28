# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""L1 corpus tests - the SECOND anchor of the Gate-3a dual verification.

The E3 applicability table from the gate prompt (researched off-line,
2026-07-14, confirmed against the fetched documents by blind extraction)
is embedded verbatim as a fixture; corpus/timeline.yaml must equal it.
A future silent edit of the timeline breaks this anchor.

ADR-008 classes enumerated here (manifest/timeline validation surface):
- (1) missing field: every source carries the full required field set;
- (2) empty value / (3) whitespace-only: required strings are non-empty
  after strip; sha256 recompute guards empty/corrupt files;
- (4) wrong type: status enum, string dates, list amending_acts;
- (5) unknown/misspelled key: timeline source_id must resolve against
  the manifest (referential variant); entry keys restricted;
- (6) boundary: applies_from/version_date match ^\\d{4}-\\d{2}-\\d{2}$
  AND are valid calendar dates;
- (7) duplicate identifiers: duplicate source ids / duplicate
  obligations rejected; duplicate YAML keys rejected by the strict
  loader (R1) which both files are parsed with.
"""
import datetime as dt
import hashlib
import pathlib
import re

import pytest

from engine.loader import load_yaml_strict

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.yaml"
TIMELINE = ROOT / "corpus" / "timeline.yaml"
RAW = ROOT / "corpus" / "raw"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE_KEYS = {
    "id", "instrument", "celex_or_eli", "version_date", "amending_acts",
    "retrieved", "sha256", "status", "file",
}
ENTRY_KEYS = {"obligation", "article", "applies_from", "condition", "source_id"}

# E3 fixture - VERBATIM from the Gate-3a prompt (do not edit to make
# tests pass; a mismatch here means the corpus diverged from the
# dual-verified table): obligation -> (applies_from, condition).
E3_TIMELINE = {
    "Art. 5 original prohibitions": ("2025-02-02", None),
    "Art. 5 NCII/CSAM (new, Omnibus)": ("2026-12-02", None),
    "Art. 4 literacy (softened)": ("2025-02-02", None),
    "Art. 50(1),(3),(4) transparency": ("2026-08-02", None),
    "Art. 50(2) marking, new systems": ("2026-08-02", None),
    "Art. 50(2) marking, legacy systems": (
        "2026-12-02", "placed on market before 2026-08-02"),
    "GPAI Art. 51-55": ("2025-08-02", None),
    "Annex III high-risk (Chapter III)": ("2027-12-02", None),
    "Annex I embedded high-risk": ("2028-08-02", None),
    "National sandboxes deadline": ("2027-08-02", None),
}

EXPECTED_CORPUS_VERSION = "aia-omnibus-oj-2026-1744"


@pytest.fixture(scope="module")
def manifest():
    return load_yaml_strict(MANIFEST)


@pytest.fixture(scope="module")
def timeline():
    return load_yaml_strict(TIMELINE)


def _dated(value, label):
    # ADR-008 (4)/(6): string type, canonical form, real calendar date.
    assert isinstance(value, str), f"{label}: date must be a string"
    assert DATE_RE.match(value), f"{label}: {value!r} not YYYY-MM-DD"
    dt.date.fromisoformat(value)


def test_corpus_version_pins_the_published_act(manifest):
    # Post-OJ refresh (ADR-016): the preOJ branch was discharged against
    # Regulation (EU) 2026/1744. The version must NOT carry the preOJ
    # marker any more - that marker is what drives corpus_status.
    assert manifest["corpus_version"] == EXPECTED_CORPUS_VERSION
    assert "preoj" not in manifest["corpus_version"].lower()


def test_corpus_status_is_final_after_the_refresh(manifest):
    # The user-visible PROVISIONAL notice is derived from the version
    # string; after the refresh the app must present the corpus as FINAL.
    from engine.render import _corpus_status
    assert _corpus_status(manifest["corpus_version"]) == "FINAL"


def test_refresh_task_is_discharged_and_traceable(manifest):
    # ADR-016: the mandatory refresh is done, and the record still says
    # what had to happen (audit trail), plus when and with what result.
    task = manifest["refresh_task"]
    assert task["mandatory"] is False
    assert "corpus_version" in task["action"]
    assert task["completed"] == "2026-07-28"
    assert "ZERO divergences" in task["result"]


def test_published_act_is_a_final_source(manifest):
    src = next(s for s in manifest["sources"] if s["id"] == "oj-2026-1744-en")
    assert src["status"] == "FINAL"
    assert "32026R1744" in src["celex_or_eli"]
    assert src["version_date"] == "2026-07-24"


def test_every_source_entry_is_complete(manifest):
    # ADR-008 (1)/(2)/(3)/(4)/(5)
    sources = manifest["sources"]
    assert isinstance(sources, list) and sources
    for src in sources:
        assert set(src) == SOURCE_KEYS, f"{src.get('id')}: keys {sorted(src)}"
        for key in SOURCE_KEYS - {"amending_acts"}:
            value = src[key]
            assert isinstance(value, str) and value.strip(), (
                f"{src.get('id')}: {key} must be a non-empty string"
            )
        assert isinstance(src["amending_acts"], list)
        assert src["status"] in ("FINAL", "PROVISIONAL")
        _dated(src["version_date"], f"{src['id']}.version_date")
        _dated(src["retrieved"], f"{src['id']}.retrieved")


def test_no_duplicate_source_ids(manifest):
    # ADR-008 (7)
    ids = [src["id"] for src in manifest["sources"]]
    assert len(ids) == len(set(ids))


def test_sha256_recomputed_from_raw_matches_recorded(manifest):
    for src in manifest["sources"]:
        path = ROOT / "corpus" / src["file"]
        assert path.is_file(), f"{src['id']}: missing {src['file']}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == src["sha256"], f"{src['id']}: sha256 mismatch"


def test_pending_section_records_excluded_draft_guidelines(manifest):
    # E4: Art. 6 classification guidelines are DRAFT -> PENDING, no file.
    pending = manifest["pending"]
    assert any("classification" in item["instrument"].lower() for item in pending)
    for item in pending:
        assert item["status"] == "PENDING"
        assert item["reason"].strip()
        assert "file" not in item and "sha256" not in item


def test_smc_definition_is_recorded_with_citation(manifest):
    # E5 (fail-closed): reference verified, source thresholds recorded,
    # E-table refutation preserved - never silently reconciled.
    smc = manifest["smc_definition"]
    assert "2025/1099" in smc["instrument"]
    assert smc["celex"] == "32025H1099"
    assert smc["e_table_refuted"].strip()


def test_timeline_entries_are_well_formed(manifest, timeline):
    # ADR-008 (1)/(4)/(5)/(6)
    ids = {src["id"] for src in manifest["sources"]}
    entries = timeline["entries"]
    assert isinstance(entries, list) and entries
    for entry in entries:
        assert set(entry) <= ENTRY_KEYS and {
            "obligation", "article", "applies_from", "source_id"} <= set(entry)
        assert entry["obligation"].strip() and entry["article"].strip()
        _dated(entry["applies_from"], entry["obligation"])
        assert entry["source_id"] in ids, (
            f"{entry['obligation']}: unknown source_id {entry['source_id']!r}"
        )


def test_timeline_has_no_duplicate_obligations(timeline):
    # ADR-008 (7)
    names = [entry["obligation"] for entry in timeline["entries"]]
    assert len(names) == len(set(names))


def test_timeline_equals_the_e3_fixture(timeline):
    # THE dual-verification anchor: content equality, both directions.
    actual = {
        entry["obligation"]: (entry["applies_from"], entry.get("condition"))
        for entry in timeline["entries"]
    }
    assert actual == E3_TIMELINE
