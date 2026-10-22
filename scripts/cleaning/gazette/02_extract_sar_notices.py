#!/usr/bin/env python3
# ============================================================
# 02_extract_sar_notices.py
# Purpose: Extract page text from every in-window gazette PDF (text layer
#          first; Tesseract OCR only for pages whose text layer is empty,
#          image-only or garbled), segment it into gazette notices, and keep
#          the full text of every notice that matches the security-access-
#          restriction (SAR) patterns (Gauteng Act 10 of 1998, Ch. 7).
#          Contents-page SAR entries are parsed separately as a recall check:
#          a contents-listed SAR notice whose body was not matched gets its
#          pages force-OCR'd and is re-tested.
# Text layer: PyMuPDF (same MuPDF text layer that pdfplumber/pdftotext read;
#          about 10x faster than pdfplumber on 100-250 page issues, and it
#          renders pages for OCR in the same pass).
# Inputs:  data/cleaned/gazette/gazette_inventory.parquet (01)
#          data/raw/gazettes/pdf/...                        (01)
# Outputs: data/raw/gazettes/text_cache/<sha256>.json.gz   (page text + flags)
#          data/cleaned/gazette/extraction_log.parquet      (one row per PDF)
#          data/cleaned/gazette/sar_candidates.parquet      (one row per notice)
#          data/cleaned/gazette/contents_sar_entries.parquet (contents hits)
#          data/cleaned/gazette/all_segments.parquet        (every segment not kept as a
#                                                            candidate, 800-char head; the
#                                                            03 recall sample draws from it)
# Usage:   py -3.12 02_extract_sar_notices.py [--limit N] [--workers K]
#          Cached page text is reused, so reruns only redo segmentation.
# ============================================================

import argparse
import bisect
import gzip
import json
import logging
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from common import ocr_page, open_pdf, page_quality, setup_logging  # noqa: E402

logger = logging.getLogger("02_extract_sar_notices")

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# Notice headers, e.g. "PROVINCIAL NOTICE 909 OF 2017", "GENERAL NOTICE 1215
# OF 2021", "LOCAL AUTHORITY NOTICE 1549 OF 2017", plain "NOTICE 830 OF 2017"
# (a general notice), and Afrikaans equivalents. Whole-line match only.
NOTICE_HEADER = re.compile(
    r"(?im)^[ \t]*(?:(?P<kind>GENERAL|PROVINCIAL|LOCAL\s+AUTHORITY|PREMIER'?S?|"
    r"ALGEMENE|PROVINSIALE|PLAASLIKE\s+(?:BESTUURS|OWERHEIDS?))\s*)?"
    r"(?:NOTICE|KENNISGEWING)\s+(?:NO\.?\s*)?(?P<no>\d{1,4})\s+(?:OF|VAN)\s+"
    r"(?P<year>(?:19|20)\d\d)[ \t]*$")

KIND_NORMALISE = {
    None: "GENERAL", "GENERAL": "GENERAL", "ALGEMENE": "GENERAL",
    "PROVINCIAL": "PROVINCIAL", "PROVINSIALE": "PROVINCIAL",
    "LOCAL AUTHORITY": "LOCAL AUTHORITY", "PLAASLIKE BESTUURS": "LOCAL AUTHORITY",
    "PLAASLIKE OWERHEID": "LOCAL AUTHORITY", "PLAASLIKE OWERHEIDS": "LOCAL AUTHORITY",
    "PREMIER'S": "PREMIER", "PREMIERS": "PREMIER", "PREMIER": "PREMIER",
}


def normalise_kind(kind: str | None) -> str:
    if kind is None:
        return "GENERAL"
    return KIND_NORMALISE.get(re.sub(r"\s+", " ", kind.upper()), kind.upper())


SAR_PATTERNS = {
    # The enabling statute: Gauteng Rationalisation of Local Government
    # Affairs Act 10 of 1998 (JHB notices misname it "...of Government
    # Affairs Act"; OCR splits "10" as "1 0" and misreads "Government").
    "act_name": (r"rationali[sz]ation\s+of\s+(?:the\s+)?(?:gauteng\s+)?(?:local\s+)?"
                 r"gov\w{0,8}\s+affairs"),
    "act_name_nofairs": r"rationali[sz]ation\s+of\s+local\s+government\s*,?\s*(?:act\s*,?\s*)?1998",
    "act_name_short": r"local\s+government\s+affairs\s+act\s*,?\s*\(?\s*(?:no\.?\s*)?10\s*/\s*1998",
    "act_abbrev": r"\bRolga\b",
    "act_name_af": r"rasionalisering\s+van\s+(?:plaaslike\s+)?regerings",
    "act_number": (r"(?:act|wet),?\s*(?:no\.?\s*)?1\s?0\s+(?:of|van)\s+1998"
                   r"|\(\s*10\s*/\s*1998\s*\)"),
    # Chapter 7 (ss. 43-48) is the access-restriction chapter.
    "chapter_7": r"chapter\s+7\b",
    "section_43_48": r"\bsections?\s+4[3-8]\s*(?:\(|\b)",
    # Restriction language.
    "sar_phrase": r"security\s+access\s+restrictions?",
    "restriction_of_access": (r"restrict(?:ion|ions|ing|ed)?\s+(?:of\s+|on\s+|to\s+)?access"
                              r"(?:.{0,160}?)(?:secur|safety)"),
    "access_restriction_security": r"access\s+restrictions?\s+for\s+(?:security|safety)",
    "restrict_access_generic": r"restrict(?:ion|ions|ing|ed)?\s+(?:of\s+|on\s+|to\s+)?access",
    "access_control": r"access\s+control",
    "beperking_af": r"beperking\s+van\s+toegang",
}
SAR_RE = {k: re.compile(v, re.I | re.S) for k, v in SAR_PATTERNS.items()}
ACT_KEYS = {"act_name", "act_abbrev", "act_name_nofairs", "act_name_short", "act_name_af", "act_number"}
CH7_KEYS = {"chapter_7", "section_43_48"}
STRONG_RESTRICTION_KEYS = {"sar_phrase", "restriction_of_access",
                           "access_restriction_security", "beperking_af"}
WEAK_RESTRICTION_KEYS = {"restrict_access_generic", "access_control"}
# confidence levels treated as SAR notices downstream
SAR_POSITIVE = {"high", "medium", "contents_only"}

# Running headers/footers stripped from notice text before parsing.
RUNNING_LINES = re.compile(
    r"(?im)^.{0,40}(?:PROVINCIAL\s+GAZETTE|PROVINSIALE\s+KOERANT)\s*,?\s*\ufeff?\s*"
    r"\d{1,2}\s+\w+\s+\d{4}.{0,30}$"
    r"|^[ \t]*This gazette is also available free online at www\.gpwonline\.co\.za[ \t]*$"
    r"|^[ \t]*No\.?\s*\d{1,4}[ \t]*$")


# English citations only: Afrikaans twins ('Wet 10 van 1998') of one notice are merged
# by design and must not count as a second block.
# An "Act 10 of 1998" citation block. Two such blocks >= ACT_BLOCK_GAP characters
# apart in one segment suggest two notices merged because a header was missed.
ACT_BLOCK = re.compile(r"\bact,?\s*(?:no\.?\s*)?1\s?0\s+of\s+1998", re.I)
ACT_BLOCK_GAP = 1500


def count_act_blocks(text: str) -> int:
    """Number of separate 'Act 10 of 1998' blocks (citations < GAP chars apart
    count once)."""
    n, last = 0, None
    for m in ACT_BLOCK.finditer(text):
        if last is None or m.start() - last >= ACT_BLOCK_GAP:
            n += 1
        last = m.start()
    return n


# Weak access/security hint used only to target the recall sample (03).
WEAK_HINT = re.compile(r"\b(?:access|closure|boom|gate[sd]?|security|safety|restrict\w*)\b", re.I)


def sar_matches(text: str) -> list[str]:
    """Names of SAR patterns found in text."""
    return [k for k, rx in SAR_RE.items() if rx.search(text)]


def sar_confidence(matched: list[str]) -> str | None:
    """Confidence that a notice is a Chapter-7 access restriction.

    high   = statute + (strong restriction language or a Ch.7 section)
    medium = strong restriction language without the statute, or statute +
             weak language ("access control", "restrict access")
    low    = statute only (Act 10 of 1998 is also cited for by-laws, SRAs)
    """
    m = set(matched)
    has_act = bool(m & ACT_KEYS)
    strong = bool(m & STRONG_RESTRICTION_KEYS)
    ch7 = bool(m & CH7_KEYS)
    weak = bool(m & WEAK_RESTRICTION_KEYS)
    if has_act and (strong or ch7):
        return "high"
    if strong or (has_act and weak):
        return "medium"
    if has_act:
        return "low"
    return None


# ---------------------------------------------------------------------------
# Page extraction (worker; runs in a separate process)
# ---------------------------------------------------------------------------
def cache_path(sha: str) -> Path:
    return config.TEXT_CACHE_DIR / f"{sha}.json.gz"


def load_cache(sha: str) -> dict | None:
    p = cache_path(sha)
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def save_cache(sha: str, payload: dict) -> None:
    with gzip.open(cache_path(sha), "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)


def extract_pdf(pdf_path: str, sha: str, force_ocr_pages: tuple = ()) -> dict:
    """Page texts for one PDF. OCR only pages flagged empty/image-only/garbled
    (plus force_ocr_pages, 1-based). Cached by sha256."""
    cached = load_cache(sha)
    if cached is not None and not (set(force_ocr_pages) - set(cached.get("ocr_pages", []))):
        return cached
    t0 = time.monotonic()
    doc = open_pdf(config.REPO_ROOT / pdf_path)
    pages, ocr_pages, t_ocr = [], [], 0.0
    prior = {p["page"]: p for p in cached["pages"]} if cached else {}
    for i, page in enumerate(doc, start=1):
        if i in prior and i not in force_ocr_pages:
            pages.append(prior[i])
            if prior[i]["ocr_used"]:
                ocr_pages.append(i)
            continue
        q = page_quality(page)
        has_image = bool(page.get_image_info())
        need_ocr = (q["image_only"] or q["garbled"] or (q["empty"] and has_image)
                    or i in force_ocr_pages)
        text = q["text"]
        ocr_start = None
        if need_ocr:
            t1 = time.monotonic()
            try:
                ocr_text = ocr_page(page, config.OCR_DPI)
            except Exception as exc:  # recorded, not fatal
                ocr_text = f"[OCR ERROR: {exc}]"
            t_ocr += time.monotonic() - t1
            ocr_pages.append(i)
            # Keep the text layer too: image-only notice pages carry the
            # gazette's own notice header ("GENERAL NOTICE 1215 OF 2021") as
            # text. ocr_start marks where the OCR part begins, so headers
            # that OCR reads off a scanned submission (e.g. the original
            # notice number of a republished notice) do not split notices.
            layer = q["text"] if not q["garbled"] else ""
            ocr_start = len(layer) + 1
            text = layer + "\n" + ocr_text
        pages.append({"page": i, "words": q["words"], "alpha_share": q["alpha_share"],
                      "image_only": q["image_only"], "garbled": q["garbled"],
                      "rotated": q["rotated"],
                      "ocr_used": need_ocr, "forced_ocr": i in force_ocr_pages,
                      "ocr_start": ocr_start, "text": text})
    payload = {"sha": sha, "pdf_path": pdf_path, "n_pages": len(pages),
               "ocr_pages": sorted(set(ocr_pages)), "pages": pages,
               "seconds_total": round(time.monotonic() - t0 + (cached or {}).get(
                   "seconds_total", 0), 2),
               "seconds_ocr": round(t_ocr + (cached or {}).get("seconds_ocr", 0), 2)}
    save_cache(sha, payload)
    return payload


# ---------------------------------------------------------------------------
# Segmentation and contents
# ---------------------------------------------------------------------------
def segment_notices(pages: list[dict]) -> list[dict]:
    """Split page texts into notices at notice headers. Text before the
    first header (cover, contents) is not a notice."""
    joined, offsets, ocr_ranges = [], [], []
    pos = 0
    for p in pages:
        offsets.append((pos, p["page"]))
        joined.append(p["text"])
        ocr_start = p.get("ocr_start")
        # Headers inside OCR text are ignored when the page has a real text
        # layer (GPW typesets the notice header as text).
        if ocr_start is not None and len(p["text"][:ocr_start].split()) >= 3:
            ocr_ranges.append((pos + ocr_start, pos + len(p["text"])))
        pos += len(p["text"]) + 1
    full = "\n".join(joined)
    starts = [o[0] for o in offsets]

    def page_at(ix: int) -> int:
        return offsets[max(0, bisect.bisect_right(starts, ix) - 1)][1]

    raw_heads = [m for m in NOTICE_HEADER.finditer(full)
                 if not any(lo <= m.start() < hi for lo, hi in ocr_ranges)]
    # A header directly after another header (only whitespace between) is
    # the original header of a republished, scanned submission (e.g. LAN 1671
    # of 2017 reprints LAN 68 of 2017): keep it inside the outer notice.
    heads, embedded = [], {}
    for m in raw_heads:
        if heads and not full[heads[-1].end():m.start()].strip():
            embedded[heads[-1].start()] = int(m.group("no"))
            continue
        heads.append(m)
    notices = []
    for k, m in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(full)
        notices.append({
            "embedded_prior_notice_no": embedded.get(m.start()),
            "notice_kind": normalise_kind(m.group("kind")), "notice_no": int(m.group("no")),
            "notice_year": int(m.group("year")),
            "page_start": page_at(m.start()), "page_end": page_at(max(m.start(), end - 1)),
            "text": full[m.start():end],
        })
    # Merge consecutive segments with the same kind+number (English and
    # Afrikaans versions, or a header repeated on continuation pages).
    merged = []
    for n in notices:
        if merged and (merged[-1]["notice_kind"], merged[-1]["notice_no"]) == (
                n["notice_kind"], n["notice_no"]):
            merged[-1]["text"] += "\n" + n["text"]
            merged[-1]["page_end"] = n["page_end"]
        else:
            merged.append(n)
    return merged


CONTENTS_SECTION = re.compile(
    r"(?i)^\s*(GENERAL|PROVINCIAL|LOCAL\s+AUTHORITY|PREMIER'?S?|ALGEMENE|PROVINSIALE|"
    r"PLAASLIKE\s+(?:BESTUURS|OWERHEIDS?))\s*(?:NOTICES|KENNISGEWINGS)\b")
CONTENTS_TITLE_HINT = re.compile(
    r"rationali[sz]ation|security\s+access|restriction\s+of\s+access|access\s+restriction",
    re.I)
# Wider contents-title hints for the recall check (review WP1-M1). Deliberately
# excludes "closure"/"boom": those match street closures under the Local
# Government Ordinance and farm names ("Wonderboom"), and "section 4x" (matches the
# Municipal Systems Act s.47 performance reports). None are Ch. 7 notices.
CONTENTS_WIDE = re.compile(
    r"access\s+control|rasionalisering|beperking\s+van\s+toegang"
    r"|security\s+(?:and|&)\s+safety", re.I)
BYLAW_TITLE = re.compile(r"by-?laws?|special\s+rating|tariff|rates|policy", re.I)
_STOP = {"act", "the", "and", "for", "affairs", "government", "local", "rationalization",
         "rationalisation", "notice", "intent", "security", "access", "restriction", "street",
         "road", "avenue", "reasons", "pending", "approval", "city", "johannesburg", "1998",
         "with", "from", "that", "this"}


def title_tokens(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", title.lower()) if w not in _STOP}


def contents_sar_entries(pages: list[dict], issue_no, max_pages: int = 14) -> list[dict]:
    """SAR-looking entries on the contents pages.

    With reading-order text a contents row is 'notice_no  title ... gazette_no
    page'; long titles wrap onto following lines. Section headings ('GENERAL
    NOTICES', 'LOCAL AUTHORITY NOTICES') give the notice kind, which matters
    because provincial and local-authority notices have separate number
    series. Where the leading number is the gazette number (older layouts),
    the notice number is left as None and matching falls back to the title.
    """
    out = []
    kind = None
    for p in pages[:max_pages]:
        text = p["text"]
        lines = [ln.strip() for ln in text.splitlines()]
        # Contents end where notices start. A page that still looks like a
        # contents page (section headings / dotted leaders / several numbered
        # rows) is kept even if it quotes a header-like line (review WP1-M1).
        contents_like = sum(bool(CONTENTS_SECTION.match(ln) or re.search(r"\.{4,}", ln)
                                 or re.match(r"^\d{1,4}\s+\D.*\s\d{1,4}\s+\d{1,4}$", ln))
                            for ln in lines)
        if NOTICE_HEADER.search(text) and contents_like < 3:
            break
        numbered = [int(m.group(1)) for ln in lines
                    if (m := re.match(r"^(\d{1,4})\s+\D", ln))]
        gazette_no_layout = bool(numbered) and issue_no is not None and (
            sum(n == issue_no for n in numbered) / len(numbered) > 0.5)
        for i, ln in enumerate(lines):
            sec = CONTENTS_SECTION.match(ln)
            if sec:
                kind = normalise_kind(sec.group(1))
                continue
            m = re.match(r"^(\d{1,4})\s+(\D.*)$", ln)
            if not m:
                continue
            parts = [m.group(2)]
            for nxt in lines[i + 1:i + 4]:
                if re.search(r"\.{3,}", parts[-1]) or re.match(r"^\d{1,4}(?:\s|$)", nxt) \
                        or CONTENTS_SECTION.match(nxt) or not nxt:
                    break
                parts.append(nxt)
            title = " ".join(parts)
            title = re.sub(r"[\s.…]*\.{3,}.*$", "", title)
            title = re.sub(r"\s+\d{1,4}\s+\d{1,4}\s*$", "", title).strip(" .\t")
            conf = sar_confidence(sar_matches(title)) if title else None
            if not title or not (CONTENTS_TITLE_HINT.search(title) or conf
                                 or CONTENTS_WIDE.search(title)):
                continue
            # the statute is also cited for by-laws: not an access restriction
            if conf in (None, "low") and BYLAW_TITLE.search(title):
                continue
            out.append({
                "contents_page": p["page"],
                "contents_kind": kind,
                "contents_notice_no": None if gazette_no_layout else int(m.group(1)),
                "contents_layout": "gazette_no_first" if gazette_no_layout else "notice_no_first",
                "contents_title": re.sub(r"\s+", " ", title)[:400],
            })
    seen, uniq = set(), []
    for e in out:
        key = (e["contents_kind"], e["contents_notice_no"], e["contents_title"][:60])
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def clean_notice_text(text: str) -> str:
    text = RUNNING_LINES.sub("", text)
    text = text.replace(" ", " ").replace("﻿", "").replace("\r", "")
    text = re.sub(r"[ \t\xa0]{2,}", "  ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _entry_matches(e: dict, n: dict) -> bool:
    """Does contents entry e refer to body notice n?"""
    if e["contents_notice_no"] is not None:
        if e["contents_notice_no"] != n["notice_no"]:
            return False
        return e["contents_kind"] is None or e["contents_kind"] == n["notice_kind"]
    tok = title_tokens(e["contents_title"])
    if not tok:
        return False
    body = n["text"][:3000].lower()
    return sum(t in body for t in tok) / len(tok) >= 0.6


TITLE_SAR = re.compile(
    r"security\s+access|restrict\w*\s+(?:of\s+|on\s+|to\s+)?access|access\s+restriction"
    r"|access\s+control|closure|boom|security\s+(?:and|&)\s+safety|section\s+4[3-8]"
    r"|beperking\s+van\s+toegang", re.I)


def body_title(n: dict) -> str | None:
    """The contents-style title GPW prints under each notice header
    ('1671   Rationalisation of ... Act, 1998: <subject>   301'), if any."""
    lines = n["text"].splitlines()[1:8]
    for k, ln in enumerate(lines):
        m = re.match(rf"^\s*{n['notice_no']}\s{{2,}}(\S.*)$", ln)
        if m:
            title = m.group(1)
            nxt = lines[k + 1].strip() if k + 1 < len(lines) else ""
            if nxt and not re.match(r"^\d{1,4}$", nxt) and len(nxt) < 200:
                title += " " + nxt
            title = re.sub(r"\s{2,}\d{1,4}\s*$", "", title).strip()
            return re.sub(r"\s+", " ", title)[:400]
    return None


def detect(notices: list[dict]) -> list[dict]:
    """Notices matching any SAR pattern, with the matched pattern names.

    Notices whose title is a by-law, tariff or policy and carries no
    restriction language are demoted to 'low' (the statute is cited as the
    by-law's enabling Act; long by-laws mention access/safety in passing).
    """
    found = []
    for n in notices:
        matched = sar_matches(n["text"])
        conf = sar_confidence(matched)
        if not conf:
            continue
        title = body_title(n)
        demoted = False
        if title and BYLAW_TITLE.search(title) and not TITLE_SAR.search(title):
            conf, demoted = "low", True
        nb = count_act_blocks(n["text"])
        found.append({**n, "body_title": title, "sar_patterns": ";".join(matched),
                      "n_act_blocks": nb, "flag_multi_notice": nb > 1,
                      "sar_confidence": conf, "demoted_bylaw_title": demoted})
    return found


def positive(cands: list[dict]) -> list[dict]:
    return [c for c in cands if c["sar_confidence"] in SAR_POSITIVE]


def process_issue(row: dict) -> dict:
    """Worker: extract, segment, detect. Returns log row, candidates, contents."""
    payload = extract_pdf(row["local_path"], row["sha256"])
    issue_no = row.get("issue_no")
    issue_no = None if issue_no is None or pd.isna(issue_no) else int(issue_no)
    notices = segment_notices(payload["pages"])
    contents = contents_sar_entries(payload["pages"], issue_no)
    cands = detect(notices)

    # Recall check: contents-listed SAR notices without a SAR-positive body.
    missing = [e for e in contents if not any(_entry_matches(e, c) for c in positive(cands))]
    forced = []
    if missing:
        segs = [n for n in notices if any(_entry_matches(e, n) for e in missing)]
        pages_to_ocr = set()
        for n in segs:
            pages_to_ocr |= set(range(n["page_start"], n["page_end"] + 1))
        forced = sorted(pages_to_ocr - set(payload["ocr_pages"]))
        if forced:
            payload = extract_pdf(row["local_path"], row["sha256"], tuple(forced))
            notices = segment_notices(payload["pages"])
            cands = detect(notices)
        # A segment that still fails the patterns but is contents-listed as
        # SAR is kept, flagged, so no contents-listed notice is silently lost.
        for e in missing:
            if any(_entry_matches(e, c) for c in positive(cands)):
                continue
            for n in notices:
                head = n["text"][:600]
                if BYLAW_TITLE.search(head) and not TITLE_SAR.search(head):
                    continue   # contents title vague, body is a by-law
                if _entry_matches(e, n):
                    cands = [c for c in cands if (c["notice_kind"], c["notice_no"]) != (
                        n["notice_kind"], n["notice_no"])]
                    cands.append({**n, "body_title": body_title(n),
                                  "sar_patterns": "contents_only",
                                  "n_act_blocks": count_act_blocks(n["text"]),
                                  "flag_multi_notice": count_act_blocks(n["text"]) > 1,
                                  "sar_confidence": "contents_only",
                                  "demoted_bylaw_title": False})
                    break

    kept = {(c["notice_kind"], c["notice_no"], c["notice_year"]) for c in cands}
    segments = [{"inventory_row": row["row_id"], "notice_kind": n["notice_kind"],
                 "notice_no": n["notice_no"], "notice_year": n["notice_year"],
                 "page_start": n["page_start"], "page_end": n["page_end"],
                 "body_title": body_title(n), "n_act_blocks": count_act_blocks(n["text"]),
                 "weak_hint": bool(WEAK_HINT.search(n["text"])),
                 "sar_matches": ";".join(sar_matches(n["text"])),
                 "text_head": clean_notice_text(n["text"][:800])}
                for n in notices
                if (n["notice_kind"], n["notice_no"], n["notice_year"]) not in kept]

    page_ocr = {p["page"]: p["ocr_used"] for p in payload["pages"]}
    for c in cands:
        c["ocr_used"] = any(page_ocr.get(i, False)
                            for i in range(c["page_start"], c["page_end"] + 1))
        c["text_clean"] = clean_notice_text(c["text"])
        hits = [e for e in contents if _entry_matches(e, c)]
        c["in_contents"] = bool(hits)
        c["contents_title"] = hits[0]["contents_title"] if hits else None
        c["inventory_row"] = row["row_id"]
    for e in contents:
        e["found_in_body"] = any(_entry_matches(e, c) for c in positive(cands))
        e["inventory_row"] = row["row_id"]

    log = {"inventory_row": row["row_id"], "sha256": row["sha256"],
           "n_pages": payload["n_pages"], "n_ocr_pages": len(payload["ocr_pages"]),
           "n_image_only": sum(p["image_only"] for p in payload["pages"]),
           "n_garbled": sum(p["garbled"] for p in payload["pages"]),
           "n_rotated": sum(p.get("rotated", False) for p in payload["pages"]),
           "n_forced_ocr": len(forced), "n_notices": len(notices),
           "n_sar_candidates": len(cands), "n_contents_sar": len(contents),
           "seconds_total": payload["seconds_total"], "seconds_ocr": payload["seconds_ocr"]}
    return {"log": log, "cands": cands, "contents": contents, "segments": segments}


def main():
    setup_logging("02_extract_sar_notices")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="process first N issues only")
    ap.add_argument("--workers", type=int, default=config.N_WORKERS)
    args = ap.parse_args()

    inv = pd.read_parquet(config.INVENTORY)
    inv["row_id"] = inv.index
    ok = inv["fetch_status"].isin(["cached", "downloaded"]) & inv["sha256"].notna()
    todo = inv[ok & inv["window"].notna() & inv["is_primary_copy"]]
    logger.info("Inventory %d files; %d in-window unique PDFs to process", len(inv), len(todo))
    if args.limit:
        todo = todo.head(args.limit)

    rows = todo[["row_id", "local_path", "sha256", "issue_no"]].to_dict("records")
    logs, cands, contents, segments = [], [], [], []
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_issue, r): r for r in rows}
        for k, fut in enumerate(as_completed(futs), start=1):
            r = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:
                logger.error("FAILED %s: %s", r["local_path"], exc)
                logs.append({"inventory_row": r["row_id"], "sha256": r["sha256"],
                             "error": str(exc)[:300]})
                continue
            logs.append(res["log"])
            cands.extend(res["cands"])
            contents.extend(res["contents"])
            segments.extend(res["segments"])
            if k % 50 == 0:
                logger.info("%d/%d issues | %d SAR candidates | %.0f s elapsed",
                            k, len(rows), len(cands), time.monotonic() - t0)

    meta_cols = ["row_id", "source", "listing_name", "local_path", "issue_date", "issue_no",
                 "issue_type", "window", "withdrawn_flag", "n_pages", "meta_conflict"]
    meta = inv[meta_cols].rename(columns={"row_id": "inventory_row"})
    log_df = pd.DataFrame(logs).merge(meta.drop(columns=["n_pages"]), on="inventory_row",
                                      how="left")
    log_df.to_parquet(config.EXTRACTION_LOG, index=False)

    cand_df = pd.DataFrame(cands)
    if not cand_df.empty:
        cand_df = cand_df.merge(meta.drop(columns=["n_pages"]), on="inventory_row", how="left")
        # One row per notice across the whole pilot: the same notice can
        # appear in two files only if the files differ (e.g. withdrawn copy).
        cand_df = cand_df.sort_values(["issue_date", "issue_no", "notice_no"]).reset_index(drop=True)
    cand_df.to_parquet(config.SAR_CANDIDATES, index=False)
    seg_df = pd.DataFrame(segments)
    if not seg_df.empty:
        seg_df = seg_df.merge(meta[["inventory_row", "issue_date", "issue_no", "window",
                                    "local_path"]], on="inventory_row", how="left")
    seg_df.to_parquet(config.ALL_SEGMENTS, index=False)
    cont_df = pd.DataFrame(contents)
    if not cont_df.empty:
        cont_df = cont_df.merge(meta[["inventory_row", "issue_date", "issue_no", "window"]],
                                on="inventory_row", how="left")
    cont_df.to_parquet(config.CONTENTS_ENTRIES, index=False)

    logger.info("Processed %d PDFs in %.0f s", len(log_df), time.monotonic() - t0)
    if "n_ocr_pages" in log_df:
        n_pages, n_ocr = log_df["n_pages"].sum(), log_df["n_ocr_pages"].sum()
        logger.info("Pages: %d total, %d OCR'd (%.1f%%)", n_pages, n_ocr,
                    100 * n_ocr / max(1, n_pages))
    logger.info("SAR candidates: %d (confidence %s)", len(cand_df),
                cand_df["sar_confidence"].value_counts().to_dict() if len(cand_df) else {})
    logger.info("Contents SAR entries: %d, found in body: %d", len(cont_df),
                int(cont_df["found_in_body"].sum()) if len(cont_df) else 0)


if __name__ == "__main__":
    main()
