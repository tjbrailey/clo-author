#!/usr/bin/env python3
# ============================================================
# 03_parse_notices.py
# Purpose: Parse SAR notice candidates (02) into one structured row per
#          notice: gazette date/number/type, notice number, municipality,
#          reference number (verbatim + parsed), stage, restriction type,
#          suburb, streets, applicant, s.4.7 affected-persons count, PSC
#          provider, validity period, and parse-confidence flags. Fields that
#          cannot be read are left NA with a reason (never guessed).
#          Also draws the manual-validation sample (precision strata plus
#          recall strata: rejected low-confidence, unflagged, merged-notice).
# Inputs:  data/cleaned/gazette/sar_candidates.parquet, all_segments.parquet (02)
# Outputs: data/cleaned/gazette/sar_notices_jhb_pilot.parquet
#          data/cleaned/gazette/validation_sample.csv  (precision + recall strata)
# Usage:   py -3.12 03_parse_notices.py
# Notes:   Rows cover all Gauteng municipalities; `is_jhb` flags Johannesburg.
#          A notice republished in several issues (same kind, number, year)
#          is one row; `n_publications` and the first/last dates record it.
#          Stage rules and their evidence phrases are in STAGE_RULES; the
#          matched phrase is stored in `stage_evidence` for audit.
# ============================================================

import logging
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from common import is_missing_text, setup_logging  # noqa: E402

logger = logging.getLogger("03_parse_notices")

SEED = 20260930
N_VALIDATION = 30
SAR_POSITIVE = {"high", "medium", "contents_only"}

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12,
                "eighteen": 18, "twenty-four": 24, "thirty-six": 36}


def _norm(text: str) -> str:
    """Collapse whitespace (OCR and sorted text layers pad with spaces)."""
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------------------
# Municipality
# ---------------------------------------------------------------------------
_METRO_RE = {k: [re.compile(p, re.I) for p in v] for k, v in config.METRO_PATTERNS.items()}
_TOWN_RE = {k: [re.compile(p, re.I) for p in v] for k, v in config.METRO_TOWN_FALLBACK.items()}


def parse_municipality(text: str, title: str | None) -> tuple[str, str]:
    """(municipality, reason). Earliest metro mention in the notice head
    (title + first 1,200 chars) wins; else in the whole notice."""
    for zone_name, zone in (("head", _norm((title or "") + " " + text[:1200])),
                            ("body", _norm(text))):
        hits = []
        for metro, pats in _METRO_RE.items():
            for p in pats:
                m = p.search(zone)
                if m:
                    hits.append((m.start(), metro))
        if hits:
            return sorted(hits)[0][1], f"first metro mention in {zone_name}"
    zone = _norm((title or "") + " " + text)
    hits = []
    for metro, pats in _TOWN_RE.items():
        for p in pats:
            m = p.search(zone)
            if m:
                hits.append((m.start(), metro, m.group(0)))
    if hits:
        _, metro, town = sorted(hits)[0]
        return metro, f"town fallback: '{town}'"
    return "unknown", "no municipality or known town named"


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------
# Evaluated in order on the notice head (title + first 1,500 chars, with
# boilerplate removed); the first rule that fires sets the stage.
BOILERPLATE = [
    # JHB intent notices: "...will result in restriction permit being revoked"
    r"violation[^.]{0,200}?revoked",
    # JHB intent notices: "this provision interim approval should not be
    # considered ... a final approval" (states what the notice is NOT)
    r"should\s+not\s+be\s+considered[^.]{0,200}?final\s+approval",
    # standard permit condition, not a withdrawal notice
    r"council\s+may\s+withdraw\s+the\s+approval",
]
STAGE_RULES = [
    ("removal", r"notice\s+of\s+(?:the\s+)?withdrawal|hereby\s+withdraw|has\s+withdrawn"
                r"|revocation\s+of|hereby\s+revoke|removal\s+of\s+(?:the\s+)?(?:security\s+)?"
                r"(?:access\s+)?restriction|cancell?ation\s+of\s+(?:the\s+)?(?:security\s+)?"
                r"(?:access\s+)?restriction|lifting\s+of\s+(?:the\s+)?restriction"),
    ("extension", r"continuation\s+of\s+the\s+restriction|approved\s+the\s+continuation"
                  r"|extension\s+of\s+(?:the\s+)?(?:period|approval|restriction|validity)"
                  r"|extend(?:ed|s)?\s+(?:the\s+)?(?:period|approval|validity)"),
    ("renewal", r"\brenewal\b|\brenew(?:ed)?\b|re-?approval|subsequent\s+application"),
    ("intent", r"notice\s+of\s+(?:the\s+)?intent(?:ion)?|intention\s+to\s+(?:restrict|approve|impose)"
               r"|intends\s+to\s+(?:restrict|approve|impose)|pending\s+approval"
               r"|interim\s+approval|proposed\s+(?:security\s+)?(?:access\s+)?restriction"
               r"|section\s+44\s*\(\s*1\s*\)\s*\(\s*c\s*\)"),
    ("final_approval", r"final\s+approval|notice\s+of\s+final|has\s+imposed\s+a\s+restriction"
                       r"|hereby\s+impose|has\s+(?:been\s+)?(?:granted|approved)\s+"
                       r"(?:the\s+)?(?:security\s+)?(?:access\s+)?restriction"
                       r"|authori[sz]e[sd]?\b.{0,120}?\bto\s+restrict\s+access"
                       r"|section\s+45\s*\(\s*3\s*\)"),
]
_STAGE_RE = [(s, re.compile(p, re.I | re.S)) for s, p in STAGE_RULES]
_BOILER_RE = [re.compile(p, re.I | re.S) for p in BOILERPLATE]
POLICY_RE = re.compile(r"(?:review|draft|amendment)\s+of\s+the\s+security\s+access\s+restriction"
                       r"s?\s+policy|security\s+access\s+restrictions?\s+policy", re.I)


def _clean_head(text: str, title: str | None) -> str:
    head = _norm((title or "") + " " + text[:1500])
    for rx in _BOILER_RE:
        head = rx.sub(" ", head)
    return head


def _match_stage(head: str, skip: tuple = ()) -> tuple[str, re.Match | None]:
    """Stage rules in priority order removal > extension > renewal, then the
    EARLIER match of intent / final_approval. A final-approval notice cites
    'section 44(1)(c)' in its body, and the title ('Final approval and
    promulgation notice') comes first in `head`, so position decides
    (review WP1-M2; 3 final notices had been coded intent)."""
    hits = {st: rx.search(head) for st, rx in _STAGE_RE if st not in skip}
    for st in ("removal", "extension", "renewal"):
        if hits.get(st):
            return st, hits[st]
    ti, tf = hits.get("intent"), hits.get("final_approval")
    if ti and tf:
        return ("intent", ti) if ti.start() <= tf.start() else ("final_approval", tf)
    if ti:
        return "intent", ti
    if tf:
        return "final_approval", tf
    return "unknown", None


def parse_procedural_stage(text: str, title: str | None) -> str:
    """Procedural step independent of the application type: removal,
    intent (incl. JHB interim approval), final_approval, or unknown.
    `stage` gives renewal/extension priority; this keeps the step."""
    return _match_stage(_clean_head(text, title), skip=("extension", "renewal"))[0]


def parse_stage(text: str, title: str | None) -> tuple[str, str | None, str]:
    """(stage, evidence phrase, reason)."""
    head = _norm((title or "") + " " + text[:1500])
    if POLICY_RE.search(head) and not re.search(r"specified\s+restrictions|road\s+name", head, re.I):
        return "other", POLICY_RE.search(head).group(0), "policy notice, not a closure decision"
    stage, m = _match_stage(_clean_head(text, title))
    if m:
        return stage, m.group(0)[:120], f"rule '{stage}' on notice head"
    return "unknown", None, "no stage phrase in title or notice head"


# Removal/withdrawal language ANYWHERE in the notice (boilerplate excluded):
# an audit flag for the 'no removal notices found' result, not a stage rule.
def removal_phrase_anywhere(text: str) -> bool:
    t = _norm(text)
    for rx in _BOILER_RE:
        t = rx.sub(" ", t)
    return bool(_STAGE_RE[0][1].search(t))


# ---------------------------------------------------------------------------
# Reference number
# ---------------------------------------------------------------------------
REF_EXPLICIT = re.compile(
    r"\b(?:application\s+)?ref(?:erence)?\.?\s*(?:no\.?|number|nr\.?)?\s*[:.#]?\s*"
    r"(?P<ref>[A-Z]{0,4}\s?\d{1,4}(?:\s*/\s*\d{2,4})?)\b", re.I)
REF_TITLE = re.compile(r"\bapplication\s+(?:no\.?\s*)?(?P<ref>\d{1,4})\b", re.I)
REF_TABLE_HEAD = re.compile(r"ref\.?\s*(?:no\.?)?", re.I)


def parse_ref(text: str, title: str | None) -> dict:
    """Reference number: explicit 'Ref ...' text, then 'Application NNN' in
    the title, then the JHB table's 'Application Ref. No.' column."""
    out = {"ref_verbatim": None, "ref_number": None, "ref_year": None, "ref_source": None,
           "ref_reason": None}
    head = text[:6000]
    # 1. explicit "Ref 438", "REF NO: 08/2017" (skip the JHB table header
    #    "Application Ref. No." which is followed by a column name, not digits)
    for m in REF_EXPLICIT.finditer(head):
        ref = m.group("ref").strip()
        if not re.search(r"\d", ref):
            continue
        out["ref_verbatim"] = _norm(m.group(0))
        nums = re.findall(r"\d+", ref)
        out["ref_number"] = int(nums[0])
        if len(nums) > 1:
            y = int(nums[1])
            out["ref_year"] = y + 2000 if y < 100 else y
        out["ref_source"] = "explicit"
        return out
    # 2. title "Application 382, Atholl"
    if title:
        m = REF_TITLE.search(title)
        if m:
            out.update(ref_verbatim=_norm(m.group(0)), ref_number=int(m.group("ref")),
                       ref_source="title")
            return out
    # 3. JHB table ('Suburb | Applicant | Application Ref. No. | Road Name |
    #    Type | Hours'): on text layers columns are separated by 2+ spaces,
    #    so the Ref cell is a 1-4 digit token standing alone between column
    #    gaps. OCR rows lose the gaps; there a single-space fallback is used
    #    and ref_source says so. A blank Ref cell gives NA, not a guess.
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if re.search(r"\bsuburb\b", ln, re.I) and (REF_TABLE_HEAD.search(ln) or any(
                REF_TABLE_HEAD.search(x) for x in lines[i + 1:i + 3])):
            block = lines[i + 1:i + 8]
            gapped = any(re.search(r"\S\s{2,}\S", b) for b in block)
            for data in block:
                if REF_TABLE_HEAD.search(data) and not re.search(r"\d", data):
                    continue
                if not data.strip():
                    continue
                if gapped:
                    m = re.search(r"(?:^|\s{2,})(\d{1,4})(?:\s{2,}|\s*$)", data)
                    if m and int(m.group(1)) > 0:
                        out.update(ref_verbatim=_norm(data)[:160], ref_number=int(m.group(1)),
                                   ref_source="table_column")
                        return out
                    continue
                for tok in re.finditer(r"(?<![\d:./hH-])(\d{1,4})(?![\d:./-])", data):
                    val = int(tok.group(1))
                    before = data[max(0, tok.start() - 12):tok.start()]
                    after = data[tok.end():tok.end() + 16]
                    if val == 0 or re.search(r"(?i)(?:ext(?:ension)?s?\.?|erf|portion|no\.?)\s*$",
                                             before):
                        continue
                    if re.match(rf"(?i)\s?(?:st|nd|rd|th)?\s?(?:[A-Za-z]+\s)?(?:{STREET_SUFFIX})\b"
                                r"|\s*x\b|\s*-?\s*h(?:ou)?r|\s*[:h]\d|\s*(?:am|pm)\b", after):
                        continue   # street no., '1 x gate', hours, times
                    out.update(ref_verbatim=_norm(data)[:160], ref_number=val,
                               ref_source="table_column_ocr")
                    return out
            break
    out["ref_reason"] = "no reference number found"
    return out


# ---------------------------------------------------------------------------
# Restriction type
# ---------------------------------------------------------------------------
TYPE_PATTERNS = {
    "manned_boom": r"manned\s+boom|boom[^.;\n]{0,40}\bmanned\b|(?:guard|security)[^.;\n]{0,40}boom"
                   r"|boom[^.;\n]{0,40}(?:guard|security\s+officer)",
    "boom": r"\bboom",
    "gate": r"\bgates?\b",
    "palisade": r"palisade",
    "fence": r"\bfenc(?:e|ing)\b",
    "manned_point": r"\bmanned\b|guard\s*house|24\s*-?\s*h(?:ou)?r?s?\.?\s+(?:manned|guard)",
}
_TYPE_RE = {k: re.compile(v, re.I) for k, v in TYPE_PATTERNS.items()}


def parse_restriction(text: str) -> dict:
    """Flags per restriction type and a primary type (manned boom > boom >
    gate > palisade > other). Conditions boilerplate ('gates must not be
    locked') counts as gate evidence only if nothing more specific exists."""
    body = _norm(text)
    flags = {f"has_{k}": bool(rx.search(body)) for k, rx in _TYPE_RE.items()}
    if flags["has_manned_boom"]:
        primary = "manned_boom"
    elif flags["has_boom"]:
        primary = "boom"
    elif flags["has_gate"]:
        primary = "gate"
    elif flags["has_palisade"]:
        primary = "palisade"
    elif flags["has_fence"]:
        primary = "other"
    else:
        primary = "unknown"
    return {"restriction_type": primary, **flags}


# ---------------------------------------------------------------------------
# Place, streets, applicant
# ---------------------------------------------------------------------------
STREET_SUFFIX = (r"Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Close|Crescent|Cres|Lane|Way|Place"
                 r"|Boulevard|Circle|Terrace|Row|Walk|Link|Loop|Mews")
STREET_RE = re.compile(
    rf"\b((?:[A-Z][A-Za-z'\-]+|\d+(?:st|nd|rd|th))(?:\s+[A-Z][A-Za-z'\-]+){{0,3}})\s+"
    rf"(?:{STREET_SUFFIX})\b\.?")
STREET_TOKEN_STOP = {
    "security", "access", "restriction", "restrictions", "of", "suburb", "applicant",
    "application", "hours", "relaxation", "type", "name", "approved", "specified", "ref",
    "registration", "committee", "association", "residents", "resident", "npc", "and", "at",
    "its", "near", "intersection", "with", "the", "separate", "pedestrian", "gate", "boom",
    "manned", "palisade", "cnr", "corner", "extension", "ext", "extensions", "that", "remainder",
    "regional", "planners", "temporary", "hour", "forum", "community", "estate", "trust",
    "foundation"}
STREET_STOP = {"The", "This", "That", "Any", "No", "Such", "Main Road", "Public", "Johannesburg",
               "Helen Joseph", "Sauer", "Pretorius", "Braamfontein", "Hendrik Potgieter",
               "Van Riebeeck", "Cnr", "Corner", "Civic", "Municipal", "Traffic Engineering"}
TOWNSHIP_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z'\-]+\s+){0,3}[A-Z][A-Za-z'\-]+(?:\s+Ext(?:ension)?s?\.?\s*\d+"
    r"(?:\s*(?:,|and|&)\s*\d+)*)?)\s+(?:Township|Dorp|AH|A\.H\.|Agricultural\s+Holdings)\b")
APPLICANT_RE = re.compile(
    r"\b((?:[A-Z0-9][\w'&\-]*\s+){1,6}?(?:Residents?'?\s+Association|Ratepayers?'?\s+Association"
    r"|Community\s+(?:Forum|Association|Trust)|Home\s*owners?'?\s+Association|HOA"
    r"|NPC|Trust|Security\s+(?:Initiative|Village|Company)|Neighbourhood\s+Watch|Foundation"
    r"|Association|Forum|Committee|Village))\b")
APPLICANT_STOP = re.compile(r"^(?:The|This|Johannesburg\s+Roads|Metropolitan|Municipal|City"
                            r"|Separate|Pedestrian|Gate|Boom|Hours?|Road|Street|Avenue|North"
                            r"|South|East|West|Remainder|Suburb|Applicant|Application)\b|^\d", re.I)
APPLICANT_GENERIC = re.compile(r"^(?:residents?'?\s+association|association|community\s+forum"
                               r"|forum|committee|trust|npc|village|foundation)$", re.I)


def parse_streets(text: str) -> list[str]:
    """Street names mentioned in the notice body (addresses of the
    municipality/JRA offices are removed)."""
    body = re.split(r"(?i)comments\s+must|objections?\s+(?:to|against)|further\s+particulars"
                    r"|may\s+be\s+inspected|lodge\s+such\s+comments", text)[0]
    found = []
    for m in STREET_RE.finditer(body.replace("\n", " ")):
        toks = _norm(m.group(1)).split(" ")
        # drop leading words that belong to table headers or neighbouring
        # cells ("Suburb Applicant Application Road" -> nothing)
        while toks and (toks[0].lower().strip("'") in STREET_TOKEN_STOP
                        or (toks[0].isupper() and len(toks) > 1)):
            toks = toks[1:]
        if not toks or any(t.lower() in STREET_TOKEN_STOP for t in toks):
            continue
        stem = " ".join(toks)
        suffix = _norm(m.group(0))[len(_norm(m.group(1))):].strip().rstrip(".")
        name = f"{stem} {suffix}"
        if stem in STREET_STOP or any(s in stem for s in ("Helen Joseph", "Sauer", "Hendrik")):
            continue
        if len(stem) < 3:
            continue
        if name not in found:
            found.append(name)
    return found


def parse_suburb(text: str, title: str | None, metro: str) -> tuple[str | None, str]:
    """(suburb, source). Order: township phrase in body, JHB table first
    column, subject after the colon in the title."""
    body = _norm(text[:4000])
    m = TOWNSHIP_RE.search(body)
    if m and not re.match(r"(?i)^(the|in|at|of|and)\b", m.group(1)):
        sub = re.split(rf"\b(?:{STREET_SUFFIX})\b\.?\s+", _norm(m.group(1)))[-1]
        sub = re.sub(r"(?i)^(?:the|at|to|in)\s+", "", sub).strip()
        if sub:
            return sub, "township_phrase"
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if re.search(r"\bsuburb\b", ln, re.I):
            for data in lines[i + 1:i + 6]:
                d = data.strip(" |")
                if not d or REF_TABLE_HEAD.fullmatch(d) or re.match(r"(?i)^(application|ref|no\.?)\b", d):
                    continue
                cell = re.split(r"\s{2,}|\|", d)[0].strip()
                cell = re.sub(r"(?i),?\s*(johannesburg|joburg)\b.*$", "", cell).strip(" ,")
                if cell and not re.search(r"\d{2,}", cell) and len(cell) <= 60:
                    return cell, "table_first_column"
                break
            break
    if title and ":" in title:
        subject = title.split(":", 1)[1]
        subject = re.sub(r"(?i)notice\s+of\s+intent(?:ion)?\s+for\s+the\s+security\s+access\s+"
                         r"restriction(?:\s+of)?|application\s+\d+,?", "", subject)
        subject = subject.strip(" ,.;")
        if subject and len(subject) <= 120 and not re.search(
                r"(?i)street/road|pending|specified\s+restrictions|various|notice\s+in\s+terms",
                subject):
            return subject, "title_subject"
    return None, "no suburb/township phrase, table or title subject"


def parse_applicant(text: str, title: str | None) -> tuple[str | None, str]:
    for source, zone in (("title", title or ""), ("body", _norm(text[:5000]))):
        for m in APPLICANT_RE.finditer(zone):
            cand = _norm(m.group(1))
            cand = re.sub(r"^(?:Authori[sz]e[sd]?|by|the|to|from|of)\s+", "", cand, flags=re.I)
            cand = re.sub(r"^(?:(?:RESIDENTS?|SECURITY|ACCESS|RESTRICTION|APPROVED|Hours)\s+)+",
                          "", cand)
            if APPLICANT_STOP.match(cand) or APPLICANT_GENERIC.match(cand) or len(cand) < 6:
                continue
            return cand, source
    return None, "no association/forum/NPC/trust name found"


# ---------------------------------------------------------------------------
# s.4.7 count, PSC provider, validity
# ---------------------------------------------------------------------------
AFFECTED_RE = re.compile(
    r"(?P<n>\d[\d ,]{0,6}\d|\d)\s+(?:affected\s+)?(?P<unit>residents|persons|people|households"
    r"|properties|erven|stands|houses|dwellings|units)\b(?=[^.]{0,80}(?:affect|within|inside"
    r"|enclos|restrict))", re.I)
AFFECTED_RE2 = re.compile(r"(?:affected|number\s+of)\s+(?:residents|persons|households|properties"
                          r"|erven|stands|houses)\s*(?:is|are|:|of)?\s*(?:approximately\s+)?"
                          r"(?P<n>\d[\d ,]{0,6}\d|\d)", re.I)


def parse_affected(text: str) -> tuple[float, str | None, str | None]:
    body = _norm(text)
    for rx in (AFFECTED_RE2, AFFECTED_RE):
        m = rx.search(body)
        if m:
            n = int(re.sub(r"[ ,]", "", m.group("n")))
            unit = m.groupdict().get("unit")
            return float(n), (unit or "stated").lower(), _norm(m.group(0))[:120]
    return np.nan, None, None


def _psc_companies():
    return [(name, re.compile(rx, 0 if not ic else re.I))
            for name, rx, ic in config._load_scraping_config().PSC_COMPANIES]


PSC_COMPANIES = _psc_companies()
# A bare '<Suburb> Security' is often the applicant (a residents' security
# initiative), so a company-type word is required.
PSC_GENERIC = re.compile(r"\b((?:[A-Z][\w&]*\s+){1,4}(?:Security|Protection|Guarding|Patrols?)"
                         r"\s+(?:Services|Solutions|Group|Company|\(Pty\)|Pty|Ltd|CC)\b"
                         r"(?:\s*\(?Pty\)?\s*Ltd)?)")
PSC_GENERIC_STOP = re.compile(r"(?i)^(?:the|for|of|and|access|restriction|public|safety|"
                              r"municipal|metro|city|traffic|road|security)\b")


def parse_psc(text: str) -> tuple[str | None, bool, str]:
    body = _norm(text)
    psira = bool(re.search(r"\bPSIRA\b|private\s+security\s+industry\s+regulatory", body, re.I))
    for name, rx in PSC_COMPANIES:
        if rx.search(body):
            return name, psira, "known company list (scripts/scraping/config.py)"
    for m in PSC_GENERIC.finditer(body):
        cand = _norm(m.group(1))
        if not PSC_GENERIC_STOP.match(cand) and not re.search(
                r"(?i)security\s+access|safety\s+and\s+security|security\s+reasons", cand):
            return cand, psira, "generic '<Name> Security/Protection' phrase"
    return None, psira, "no provider named"


# 'valid for N years/months', or 'for a period of N years' (years only: a
# 'period of one month' / '28 days' is the comment window, not validity).
VALIDITY_RE = re.compile(
    r"(?:valid(?:ity)?\s+(?:for|period\s+of)\s+(?:a\s+period\s+of\s+)?"
    r"(?P<w>[a-z\-]+|\d+)\s*(?:\(\s*(?P<d>\d+)\s*\)\s*)?(?P<u>years?|months?)"
    r"|(?:for\s+a\s+(?:further\s+)?)?period\s+of\s+(?P<w2>[a-z\-]+|\d+)\s*"
    r"(?:\(\s*(?P<d2>\d+)\s*\)\s*)?(?P<u2>years?))", re.I)


def parse_validity(text: str) -> tuple[float, str | None]:
    m = VALIDITY_RE.search(_norm(text))
    if not m:
        return np.nan, None
    w = m.group("w") or m.group("w2")
    d = m.group("d") or m.group("d2")
    u = (m.group("u") or m.group("u2")).lower()
    if d:
        n = int(d)
    elif w.isdigit():
        n = int(w)
    else:
        n = NUMBER_WORDS.get(w.lower())
    if n is None:
        return np.nan, _norm(m.group(0))
    months = n * 12 if u.startswith("year") else n
    return float(months), _norm(m.group(0))


# ---------------------------------------------------------------------------
# One notice
# ---------------------------------------------------------------------------
def parse_notice(text: str, title: str | None = None) -> dict:
    """All parsed fields for one notice text (used by main() and tests)."""
    title = None if title is None or is_missing_text(title) else title
    metro, metro_reason = parse_municipality(text, title)
    stage, stage_evidence, stage_reason = parse_stage(text, title)
    procedural_stage = parse_procedural_stage(text, title) if stage != "other" else "other"
    ref = parse_ref(text, title)
    rtype = parse_restriction(text)
    streets = parse_streets(text)
    suburb, suburb_source = parse_suburb(text, title, metro)
    applicant, applicant_source = parse_applicant(text, title)
    affected_n, affected_unit, affected_verbatim = parse_affected(text)
    psc, psira, psc_source = parse_psc(text)
    validity_months, validity_verbatim = parse_validity(text)
    out = {
        "municipality": metro, "municipality_reason": metro_reason,
        "stage": stage, "stage_evidence": stage_evidence, "stage_reason": stage_reason,
        "procedural_stage": procedural_stage,
        "removal_phrase_anywhere": removal_phrase_anywhere(text),
        **ref, **rtype,
        "streets": "; ".join(streets) if streets else None, "n_streets": len(streets),
        "suburb": suburb, "suburb_source": suburb_source if suburb else None,
        "suburb_reason": None if suburb else suburb_source,
        "applicant": applicant, "applicant_source": applicant_source if applicant else None,
        "applicant_reason": None if applicant else applicant_source,
        "affected_persons_n": affected_n, "affected_unit": affected_unit,
        "affected_verbatim": affected_verbatim,
        "psc_provider": psc, "psc_source": psc_source if psc else None,
        "psira_mentioned": psira,
        "validity_months": validity_months, "validity_verbatim": validity_verbatim,
    }
    return out


def parse_flags(row: dict) -> str:
    """Semicolon list of reasons to check this row by hand."""
    f = []
    if row["ocr_used"]:
        f.append("ocr_text")
    if row["sar_confidence"] != "high":
        f.append(f"detection_{row['sar_confidence']}")
    if row["stage"] == "unknown":
        f.append("stage_unknown")
    if row["municipality"] == "unknown":
        f.append("municipality_unknown")
    if row["ref_number"] is None or pd.isna(row["ref_number"]):
        f.append("ref_missing")
    elif str(row["ref_source"]).startswith("table_column"):
        f.append("ref_from_table_position")
    if row["suburb"] is None:
        f.append("suburb_missing")
    if row["restriction_type"] == "unknown":
        f.append("type_unknown")
    if row.get("flag_multi_notice"):
        f.append("possible_merged_notices")
    return ";".join(f)


# ---------------------------------------------------------------------------
# Validation sample
# ---------------------------------------------------------------------------
VALIDATE_FIELDS = ["municipality", "stage", "ref_number", "restriction_type", "suburb",
                   "streets", "applicant", "affected_persons_n", "psc_provider",
                   "validity_months"]


def allocate(counts: pd.Series, n: int) -> pd.Series:
    """Proportional allocation with a floor of min(2, stratum size) and
    largest-remainder rounding; never exceeds a stratum's size."""
    counts = counts[counts > 0]
    floor = counts.clip(upper=2)
    rest = n - floor.sum()
    if rest <= 0:
        return floor
    avail = counts - floor
    share = avail / avail.sum() * rest if avail.sum() else avail * 0
    alloc = floor + np.floor(share).astype(int)
    rem = (share - np.floor(share)).sort_values(ascending=False)
    for k in rem.index:
        if alloc.sum() >= n:
            break
        if alloc[k] < counts[k]:
            alloc[k] += 1
    return alloc.astype(int)


# Stratified precision design (n ~ 36): stage allocation as before, then a
# top-up so every level of confidence / window / municipality has >= 2 notices
# (where that many exist). Recall design: low-confidence candidates that were
# rejected, unflagged segments with weak access/security language, and
# segments that may hold two merged notices (review WP1-H1).
N_RECALL_LOW, N_RECALL_UNFLAGGED, N_MULTI_MAX = 6, 6, 4
TOPUP_DIMS = ["sar_confidence", "window", "municipality"]


def _recall_row(stratum, r, text, title, issue_type, ocr):
    return dict(sample_stratum=stratum,
                notice_id=f"{r.notice_year}-{r.notice_kind[:2]}-{int(r.notice_no):04d}",
                first_issue_date=r.issue_date, first_issue_no=r.issue_no,
                first_issue_type=issue_type, notice_kind=r.notice_kind,
                notice_no=r.notice_no, pdf_path=r.local_path,
                page_start=r.page_start, page_end=r.page_end, ocr_used=ocr,
                notice_title=title, _text=text)


def validation_sample(df: pd.DataFrame, cands: pd.DataFrame | None = None,
                      segments: pd.DataFrame | None = None) -> pd.DataFrame:
    sar = df[df["is_sar_notice"]].copy()
    rng = np.random.default_rng(SEED)
    alloc = allocate(sar["stage"].value_counts(), min(N_VALIDATION, len(sar)))
    picked, why = {}, {}
    for stage, k in alloc.items():
        pool = sar[sar["stage"] == stage].sort_values("notice_id")
        idx = rng.choice(len(pool), size=int(k), replace=False)
        for i in pool.iloc[sorted(idx)].index:
            picked[i] = True
            why[i] = f"precision:stage={stage}"
    for dim in TOPUP_DIMS:
        for level, g in sar.groupby(dim, dropna=False):
            have = sum(1 for i in g.index if i in picked)
            rest = g[[i not in picked for i in g.index]].sort_values("notice_id")
            need = min(2 - have, len(rest))
            if need > 0:
                for i in rest.iloc[sorted(rng.choice(len(rest), size=need,
                                                     replace=False))].index:
                    picked[i] = True
                    why[i] = f"precision:{dim}={level}"
    multi = sar[sar["flag_multi_notice"].astype(bool) & ~sar.index.isin(list(picked))]
    multi = multi.sort_values("notice_id")
    for i in multi.iloc[:N_MULTI_MAX].index:
        picked[i] = True
        why[i] = "recall:possible_merged_notices"
    samp = sar.loc[list(picked)].copy()
    samp["sample_stratum"] = [why[i] for i in samp.index]
    keep = ["notice_id", "first_issue_date", "first_issue_no", "first_issue_type",
            "notice_kind", "notice_no", "pdf_path", "page_start", "page_end", "ocr_used",
            "notice_title"]
    samp = samp.sort_values(["first_issue_date", "notice_id"])
    out = samp[["sample_stratum"] + keep].copy()
    out["sample_role"] = np.where(out["sample_stratum"].str.startswith("recall"),
                                  "recall", "precision")
    for f in VALIDATE_FIELDS:
        out[f"parsed_{f}"] = samp[f].values

    # Recall rows: candidates rejected as low confidence, and unflagged segments
    extra = []
    if cands is not None and len(cands):
        low = cands[cands["sar_confidence"] == "low"].sort_values(
            ["issue_date", "notice_kind", "notice_no"])
        if len(low):
            low = low.iloc[sorted(rng.choice(len(low), size=min(N_RECALL_LOW, len(low)),
                                             replace=False))]
            for r in low.itertuples():
                extra.append(_recall_row("recall:low_confidence_rejected", r, r.text_clean,
                                         r.body_title or r.contents_title, r.issue_type,
                                         r.ocr_used))
    if segments is not None and len(segments):
        pool = segments[segments["weak_hint"]].sort_values(
            ["issue_date", "notice_kind", "notice_no"])
        if len(pool):
            pool = pool.iloc[sorted(rng.choice(len(pool),
                                               size=min(N_RECALL_UNFLAGGED, len(pool)),
                                               replace=False))]
            for r in pool.itertuples():
                extra.append(_recall_row("recall:unflagged_weak_hint", r, r.text_head,
                                         r.body_title, None, None))
    if extra:
        ex = pd.DataFrame(extra)
        ex["sample_role"] = "recall"
        for f in VALIDATE_FIELDS:
            ex[f"parsed_{f}"] = None
        ex["parsed_stage"] = [parse_stage(t, ti)[0] for t, ti in zip(ex["_text"],
                                                                     ex["notice_title"])]
        ex = ex.drop(columns="_text")
        out = pd.concat([out, ex], ignore_index=True)
    for f in VALIDATE_FIELDS:
        out[f"ok_{f}"] = ""            # user: Y / N / NA-correct
        out[f"correct_{f}"] = ""       # user: value read from the PDF if N
    out["is_sar_notice_ok"] = ""       # user: Y if this is really a Ch.7 notice
    out["reviewer_notes"] = ""
    return out


def main():
    setup_logging("03_parse_notices")
    cands = pd.read_parquet(config.SAR_CANDIDATES)
    logger.info("Candidates: %d (confidence %s)", len(cands),
                cands["sar_confidence"].value_counts().to_dict())
    cands = cands[cands["sar_confidence"].isin(SAR_POSITIVE)].copy()
    cands["notice_title"] = cands["contents_title"].where(
        cands["contents_title"].notna(), cands["body_title"])

    # One row per notice: (kind, number, year). The first publication
    # supplies the text; later ones only add dates.
    cands = cands.sort_values(["issue_date", "issue_no", "page_start"])
    key = ["notice_kind", "notice_no", "notice_year"]
    pubs = cands.groupby(key).agg(
        n_publications=("issue_date", "size"),
        first_issue_date=("issue_date", "min"), last_issue_date=("issue_date", "max"),
        publication_issues=("issue_no", lambda s: ";".join(str(int(x)) for x in s)),
    ).reset_index()
    first = cands.drop_duplicates(key, keep="first")
    df = first.merge(pubs, on=key, how="left")

    parsed = [parse_notice(t, ti) for t, ti in zip(df["text_clean"], df["notice_title"])]
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(parsed)], axis=1)
    df["notice_id"] = (df["notice_year"].astype(str) + "-" + df["notice_kind"].str[:2]
                       + "-" + df["notice_no"].astype(int).astype(str).str.zfill(4))
    df["is_jhb"] = df["municipality"] == "JHB"
    # Closure decisions vs policy notices (both kept; only decisions count
    # toward notice volume).
    df["is_sar_notice"] = df["stage"] != "other"
    df["first_issue_no"] = df["issue_no"]
    df["first_issue_type"] = df["issue_type"]
    df["pdf_path"] = df["local_path"]
    # Possible re-numbered republications: same municipality, suburb, reference
    # number and stage under different notice numbers. Dedup on (kind, number,
    # year) cannot merge these, so n_notices is an upper bound (review WP1-M3).
    kk = df["suburb"].notna() & df["ref_number"].notna() & df["is_sar_notice"]
    df["dup_suspect"] = False
    df.loc[kk, "dup_suspect"] = df[kk].duplicated(
        ["municipality", "suburb", "ref_number", "stage"], keep=False)
    df["parse_flags"] = [parse_flags(r) for r in df.to_dict("records")]
    df["needs_manual_review"] = df["parse_flags"].str.contains(
        "stage_unknown|municipality_unknown|ref_missing|detection_contents_only|type_unknown"
        "|possible_merged_notices")

    cols = ["notice_id", "window", "first_issue_date", "last_issue_date", "n_publications",
            "publication_issues", "first_issue_no", "first_issue_type", "source", "pdf_path",
            "page_start", "page_end", "notice_kind", "notice_no", "notice_year",
            "notice_title", "municipality", "municipality_reason", "is_jhb", "is_sar_notice",
            "stage", "stage_evidence", "stage_reason", "procedural_stage", "removal_phrase_anywhere", "n_act_blocks",
            "flag_multi_notice", "dup_suspect", "ref_verbatim", "ref_number", "ref_year",
            "ref_source", "ref_reason", "restriction_type", "has_manned_boom", "has_boom",
            "has_gate", "has_palisade", "has_fence", "has_manned_point", "suburb",
            "suburb_source", "suburb_reason", "streets", "n_streets", "applicant",
            "applicant_source", "applicant_reason", "affected_persons_n", "affected_unit",
            "affected_verbatim", "psc_provider", "psc_source", "psira_mentioned",
            "validity_months", "validity_verbatim", "sar_confidence", "sar_patterns",
            "in_contents", "ocr_used", "withdrawn_flag", "parse_flags", "needs_manual_review",
            "text_clean"]
    df = df[cols].sort_values(["first_issue_date", "notice_id"]).reset_index(drop=True)
    df["ref_number"] = df["ref_number"].astype("Int64")
    df["ref_year"] = df["ref_year"].astype("Int64")
    df.to_parquet(config.SAR_NOTICES, index=False)
    logger.info("Wrote %d notices (%d closure decisions; %d JHB) to %s", len(df),
                int(df["is_sar_notice"].sum()), int(df["is_jhb"].sum()),
                config.SAR_NOTICES.relative_to(config.REPO_ROOT))
    logger.info("flag_multi_notice: %d | dup_suspect: %d | removal_phrase_anywhere: %d",
                int(df["flag_multi_notice"].sum()), int(df["dup_suspect"].sum()),
                int(df["removal_phrase_anywhere"].sum()))
    logger.info("Stage mix: %s", df["stage"].value_counts().to_dict())
    logger.info("Municipality mix: %s", df["municipality"].value_counts().to_dict())

    segs = pd.read_parquet(config.ALL_SEGMENTS) if config.ALL_SEGMENTS.exists() else None
    cands_all = pd.read_parquet(config.SAR_CANDIDATES)
    val = validation_sample(df, cands_all, segs)
    val.to_csv(config.VALIDATION_SAMPLE, index=False, encoding="utf-8-sig")
    logger.info("Validation sample: %d notices (%s), strata %s -> %s", len(val),
                val["sample_role"].value_counts().to_dict(),
                val["sample_stratum"].value_counts().to_dict(),
                config.VALIDATION_SAMPLE.relative_to(config.REPO_ROOT))


if __name__ == "__main__":
    main()
