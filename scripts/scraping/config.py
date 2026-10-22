# ============================================================
# config.py — Scraping pipeline configuration
# Project: Gated Communities & State Attitudes (PSC Exposure)
# ============================================================

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to repository root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "scraping"
CLEANED_DIR = REPO_ROOT / "data" / "cleaned"
CACHE_DIR = RAW_DIR / ".cache"

RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

URL_INVENTORY = RAW_DIR / "url_inventory.jsonl"
LISTINGS_CLASSIFIED = RAW_DIR / "listings_classified.parquet"
LISTINGS_GEOCODED = CLEANED_DIR / "listings_geocoded.parquet"
GEOCODE_CACHE = CACHE_DIR / "geocode_cache.json"

# ---------------------------------------------------------------------------
# Target site
# ---------------------------------------------------------------------------
BASE_DOMAIN = "property24.com"
LISTING_URL_PATTERNS = [
    "property24.com/for-sale/*",
    "property24.com/to-rent/*",
]

# ---------------------------------------------------------------------------
# Cities — slug used in Property24 URLs + standardized name + province
# ---------------------------------------------------------------------------
CITIES = [
    {"slug": "johannesburg",      "name": "Johannesburg",   "province": "Gauteng"},
    {"slug": "pretoria",          "name": "Pretoria",       "province": "Gauteng"},
    {"slug": "cape-town",         "name": "Cape Town",      "province": "Western Cape"},
    {"slug": "durban",            "name": "Durban",         "province": "KwaZulu-Natal"},
    {"slug": "port-elizabeth",    "name": "Gqeberha",       "province": "Eastern Cape"},
    {"slug": "east-london",       "name": "East London",    "province": "Eastern Cape"},
    {"slug": "bloemfontein",      "name": "Bloemfontein",   "province": "Free State"},
    {"slug": "nelspruit",         "name": "Mbombela",       "province": "Mpumalanga"},
    {"slug": "polokwane",         "name": "Polokwane",      "province": "Limpopo"},
]

# City slug → standardized name lookup
CITY_SLUG_MAP = {c["slug"]: c["name"] for c in CITIES}

# City centroid fallback (lat, lon) for geocoding failures
CITY_CENTROIDS = {
    "Johannesburg":      (-26.2041, 28.0473),
    "Pretoria":          (-25.7479, 28.2293),
    "Cape Town":         (-33.9249, 18.4241),
    "Durban":            (-29.8587, 31.0218),
    "Gqeberha":          (-33.9608, 25.6022),
    "East London":       (-32.9858, 27.8546),
    "Bloemfontein":      (-29.0852, 26.1596),
    "Mbombela":          (-25.4753, 30.9694),
    "Polokwane":         (-23.9045, 29.4688),
    "Ekurhuleni":        (-26.1496, 28.3122),
    "Tshwane":           (-25.7479, 28.2293),
    "Pietermaritzburg":  (-29.6006, 30.3794),
    "George":            (-33.9631, 22.4618),
    "Knysna":            (-34.0356, 23.0488),
    "Mossel Bay":        (-34.1833, 22.1500),
    "Welkom":            (-27.9774, 26.7358),
    "Rustenburg":        (-25.6715, 27.2420),
    "Potchefstroom":     (-26.7145, 27.0975),
}

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------
RATE_WAYBACK_CDX    = 0.5   # requests per second to Wayback CDX API
RATE_COMMONCRAWL_CDX = 1.0  # requests per second to Common Crawl CDX API
RATE_WAYBACK_FETCH  = 0.5   # requests per second fetching archived pages
RATE_LIVE_MIN       = 10    # minimum seconds between live requests
RATE_LIVE_MAX       = 30    # maximum seconds between live requests
RATE_NOMINATIM      = 1.0   # requests per second to Nominatim

LIVE_REQUEST_LIMIT  = 200   # default max requests per live scraping session
CHECKPOINT_INTERVAL = 500   # save progress every N records

# ---------------------------------------------------------------------------
# PSC / Gated Community Keywords
# ---------------------------------------------------------------------------
# Patterns are regex fragments, OR-ed within a group and matched
# case-insensitively by 04_classify_psc.py (compiled once at import).
# Full column definitions: "Data dictionary" in
# quality_reports/scrape_audit_2026-09-29.md (generated from this file).
#
# Two layers (revision 2026-09-29, coder-critic round 1 B2/B3):
#   v1 = plan-scope dictionary -> psc_flag, psc_score and the five group
#        columns. Changes vs the original list are ONLY those in the approved
#        plan or requested in review:
#          - "fingerprin" (never matched) -> "fingerprints?"
#          - bare "intercom" -> weak indicator (not in psc_flag)
#          - bare "guarded" -> "guarded" + security noun, or 24h + "guarded"
#            (it matched "burglar guarded" = burglar bars)
#          - "boundary wall", "high wall", "perimeter wall" -> weak indicator
#          - company names: word boundaries (see PSC_COMPANIES)
#   v2 = construct layer -> enclave_flag, guard_service_flag, hardening_flag.
#        Widened spellings live here, and every widening is ALSO exposed as a
#        separate cand_* column so the strategist can redefine without code.

# ---- v1 groups (plan scope) ------------------------------------------------
_GUARDED_NOUNS = (r"(?:security|access|building|complex|estate|premises|parking"
                  r"|development|community|village|block)")

# Infrastructure: strong evidence of gated estate
KEYWORDS_SECURITY_ESTATE = [
    r"\bsecurity estate\b",
    r"\bgated estate\b",
    r"\bgated community\b",
    r"\bgated complex\b",
    r"\bwalled estate\b",
    r"\bsecure estate\b",
    r"\bsecured estate\b",
    r"\benclosed estate\b",
    r"\blifestyle estate\b",
]

# Access control infrastructure
KEYWORDS_BOOM_GATE = [
    r"\bboom gate\b",
    r"\bboom.?controlled\b",
    r"\baccess boom\b",
    r"\bguarded entrance\b",
    r"\bguarded gate\b",
    r"\bgated entrance\b",
]

# Access control (general)
KEYWORDS_ACCESS_CONTROLLED = [
    r"\baccess.?controlled\b",
    r"\baccess control\b",
    r"\bcontrolled access\b",
    r"\bbiometric\b",
    r"\bfingerprints?\b",
]

# Armed response / security personnel
KEYWORDS_ARMED_RESPONSE = [
    r"\barmed response\b",
    r"\barmed guard\b",
    r"\barmed security\b",
    r"\bsecurity guard\b",
    r"\bsecurity officer\b",
    r"\b24.?hour security\b",
    r"\b24/7 security\b",
    r"\bround.?the.?clock security\b",
    r"\bon.?site security\b",
    rf"\bguarded {_GUARDED_NOUNS}\b",
    r"\b(?:24.?hour|24/7|round.?the.?clock),? guarded\b",
]

# Electric/perimeter fencing (walls moved to WEAK_INDICATOR_GROUPS["walls"])
KEYWORDS_ELECTRIC_FENCE = [
    r"\belectric.?fence\b",
    r"\belectrified.?fence\b",
    r"\belectrified perimeter\b",
    r"\bsecurity wall\b",
]

# Combined: all v1 keyword groups for psc_flag
ALL_PSC_KEYWORD_GROUPS = {
    "security_estate":  KEYWORDS_SECURITY_ESTATE,
    "boom_gate":        KEYWORDS_BOOM_GATE,
    "access_controlled": KEYWORDS_ACCESS_CONTROLLED,
    "armed_response":   KEYWORDS_ARMED_RESPONSE,
    "electric_fence":   KEYWORDS_ELECTRIC_FENCE,
}

# ---- v2 construct components ---------------------------------------------
# "24h" qualifier incl. abbreviations the v1 "24.?hour" misses (24hr, 24 hrs, 24h)
_H24 = r"(?:24.?(?:hours?|hrs?|h)\.?|24/7|round.?the.?clock)"

CONSTRUCT_COMPONENTS = {
    # Enclosed residential enclave: the development itself is gated
    "enclave": {
        "security_estate_v2": [
            r"\b(?:security|gated|walled|secured?|enclosed|lifestyle) estates?\b",
            r"\bgated communit(?:y|ies)\b",
            r"\bgated complex(?:es)?\b",
        ],
        "boom_gate_v2": [
            r"\bboom.?gat(?:e|es|ed)\b",
            r"\bboom.?controlled\b",
            r"\baccess boom\b",
            r"\bguarded entrances?\b",
            r"\bguarded gate(?:house)?s?\b",
            r"\bgated entrances?\b",
        ],
    },
    # Guarding / armed-response service (company names are added in 04)
    "guard_service": {
        "armed_response_v2": [
            r"\barmed response\b",
            r"\barmed guards?\b",
            r"\barmed security\b",
            r"\bsecurity guards?\b",
            r"\bsecurity officers?\b",
            rf"\b{_H24} (?:manned |guarded |armed )?security\b",
            r"\bmanned security\b",
            r"\bon.?site security\b",
            rf"\bguarded {_GUARDED_NOUNS}s?\b",
            rf"\b{_H24},? guarded\b",
        ],
    },
    # Physical / technological target hardening of the property or building
    "hardening": {
        "electric_fence_v2": [
            r"\belectric.?fenc(?:e|es|ed|ing)\b",
            r"\belectrified.?fenc(?:e|es|ing)\b",
            r"\belectrified perimeter\b",
            r"\bsecurity wall\b",
        ],
        "access_control_v2": [
            r"\baccess.?controlled\b",
            r"\baccess control\b",
            r"\bcontrolled access\b",
            r"\bbiometric\b",
            r"\bfinger.?prints?\b",
        ],
    },
}

# Candidate phrases: one 0/1 column each (prefix cand_). The first three are
# NOT in any construct flag (only in enclave_flag_broad); the rest mark the
# v2 widenings, so each can be switched off downstream.
CANDIDATE_PHRASES = {
    "cand_security_complex":    r"\bsecurity complex(?:es)?\b",
    "cand_secure_complex":      r"\bsecured? complex(?:es)?\b",
    "cand_security_village":    r"\bsecurity villages?\b",
    "cand_24h_abbrev_security": (r"\b24.?(?:hrs?|h|hours)\.? (?:manned |guarded |armed )?"
                                 r"security\b"),
    "cand_manned_security":     r"\bmanned security\b",
    "cand_electric_fencing":    r"\belectri(?:c|fied).?fenc(?:es|ed|ing)\b",
    "cand_finger_print":        r"\bfinger.prints?\b",
    "cand_estate_plural":       r"\b(?:security|gated|secured?|lifestyle) estates\b",
}
ENCLAVE_BROAD_CANDIDATES = ["cand_security_complex", "cand_secure_complex",
                            "cand_security_village"]

# Weak indicators: recorded as separate 0/1 columns but EXCLUDED from every
# flag and score (too common outside gated/PSC settings).
WEAK_INDICATOR_GROUPS = {
    "intercom": [r"\b(?:video.?)?intercoms?\b"],
    "walls": [r"\bboundary walls?\b", r"\bhigh walls?\b", r"\bperimeter walls?\b"],
}

# PSC company names (South African market).
# (display_name, regex, ignore_case). Word boundaries throughout, so
# "ROADThis" no longer matches ADT. Names that are ordinary English words
# ("enforce", "fidelity", "guardsman") are case-sensitive, with an explicit
# ALL-CAPS alternative for shouted listings. Trade-off: "ENFORCE" in an
# all-caps listing still matches. "Fidelity Fund Certificate" is estate-agent
# regulatory boilerplate and is excluded. Bare "Bidvest" (a conglomerate)
# and bare "Coin" are not matched. Brands are matched in list order and a
# matched span is blanked before later names are tried, so "Fidelity ADT"
# counts once.
PSC_COMPANIES = [
    ("Fidelity ADT",         r"\bFidelity\s+ADT\b",                        True),
    ("ADT",                  r"\bADT\b",                                   True),
    ("Fidelity",             r"\b(?:Fidelity|FIDELITY)\b(?!\s+(?i:fund))", False),
    ("G4S",                  r"\bG4S\b",                                   True),
    ("Chubb",                r"\bChubb\b",                                 True),
    ("Securitas",            r"\bSecuritas\b",                             True),
    ("Bidvest Protea Coin",  r"\b(?:Bidvest\s+)?Protea\s+Coin\b",          True),
    ("Enforce",              r"\b(?:Enforcer?|ENFORCER?)\b",               False),
    ("Spar Security",        r"\bSpar\s+Security\b",                       True),
    ("Stallion Security",    r"\bStallion\s+Security\b",                   True),
    ("Specialised Security", r"\bSpeciali[sz]ed\s+Security\b",             True),
    ("CSS Tactical",         r"\bCSS\s+Tactical\b",                        True),
    ("Coin Security",        r"\bCoin\s+Security\b",                       True),
    ("Gray Security",        r"\bGr[ae]y\s+Security\b",                    True),
    ("SASCO",                r"\bSASCO\b",                                 False),
    ("Guardsman",            r"\b(?:Guardsman|GUARDSMAN)\b",               False),
    ("Khulani",              r"\bKhulani\b",                               True),
]

# ---------------------------------------------------------------------------
# Property24 town slug (2nd URL segment) -> study metro (`city` column).
# 00_archive_discovery.py originally labelled every CDX hit for the prefix
# "for-sale/durban*" as Durban, which included Durbanville (Cape Town metro)
# and Durban Deep (Roodepoort, Johannesburg metro). 03 re-derives `city`
# from these slugs. Unknown town slugs map to NA and are logged.
# ---------------------------------------------------------------------------
P24_TOWN_TO_METRO = {
    # --- Original 9-city slugs ---
    "bloemfontein":   "Bloemfontein",
    "cape-town":      "Cape Town",
    "durbanville":    "Cape Town",
    "durban":         "Durban",
    "durban-north":   "Durban",
    "east-london":    "East London",
    "johannesburg":   "Johannesburg",
    "randburg":       "Johannesburg",
    "roodepoort":     "Johannesburg",
    "nelspruit":      "Mbombela",
    "polokwane":      "Polokwane",
    "port-elizabeth": "Gqeberha",
    "pretoria":       "Pretoria",
    # --- Gauteng: Johannesburg metro ---
    "sandton":        "Johannesburg",
    "fourways":       "Johannesburg",
    "bryanston":      "Johannesburg",
    "bedfordview":    "Johannesburg",
    "edenvale":       "Johannesburg",
    "midrand":        "Johannesburg",
    "alberton":       "Johannesburg",
    "germiston":      "Johannesburg",
    "soweto":         "Johannesburg",
    "alexandra":      "Johannesburg",
    "lonehill":       "Johannesburg",
    "sunninghill":    "Johannesburg",
    "northcliff":     "Johannesburg",
    "florida":        "Johannesburg",
    "krugersdorp":    "Johannesburg",
    "greenside":      "Johannesburg",
    "parkhurst":      "Johannesburg",
    "melrose":        "Johannesburg",
    "hyde-park":      "Johannesburg",
    "morningside":    "Johannesburg",
    # --- Gauteng: Ekurhuleni metro ---
    "kempton-park":   "Ekurhuleni",
    "benoni":         "Ekurhuleni",
    "boksburg":       "Ekurhuleni",
    "springs":        "Ekurhuleni",
    "brakpan":        "Ekurhuleni",
    "nigel":          "Ekurhuleni",
    # --- Gauteng: Tshwane metro ---
    "centurion":      "Tshwane",
    "hatfield":       "Tshwane",
    "menlo-park":     "Tshwane",
    "waterkloof":     "Tshwane",
    "lynnwood":       "Tshwane",
    "montana":        "Tshwane",
    "garsfontein":    "Tshwane",
    "irene":          "Tshwane",
    # --- KwaZulu-Natal ---
    "umhlanga":       "Durban",
    "ballito":        "Durban",
    "pinetown":       "Durban",
    "hillcrest":      "Durban",
    "amanzimtoti":    "Durban",
    "westville":      "Durban",
    "pietermaritzburg": "Pietermaritzburg",
    # --- Western Cape ---
    "stellenbosch":   "Cape Town",
    "paarl":          "Cape Town",
    "bellville":      "Cape Town",
    "somerset-west":  "Cape Town",
    "milnerton":      "Cape Town",
    "tableview":      "Cape Town",
    "constantia":     "Cape Town",
    "claremont":      "Cape Town",
    "wynberg":        "Cape Town",
    "fishhoek":       "Cape Town",
    "simons-town":    "Cape Town",
    "hout-bay":       "Cape Town",
    "camps-bay":      "Cape Town",
    "muizenberg":     "Cape Town",
    "tokai":          "Cape Town",
    "plumstead":      "Cape Town",
    "rondebosch":     "Cape Town",
    "goodwood":       "Cape Town",
    "brackenfell":    "Cape Town",
    "kraaifontein":   "Cape Town",
    "kuilsrivier":    "Cape Town",
    "gordons-bay":    "Cape Town",
    "strand":         "Cape Town",
    "george":         "George",
    "knysna":         "Knysna",
    "mossel-bay":     "Mossel Bay",
    # --- Gauteng: additional ---
    "bronkhorstspruit": "Tshwane",
    "lethabong":        "Ekurhuleni",
    # --- KwaZulu-Natal: additional ---
    "umhlanga-rocks":   "Durban",
    "ladysmith":        "Ladysmith",
    "umzimkhulu":       "Umzimkhulu",
    # --- Western Cape: additional Cape Town suburbs ---
    "blue-downs":       "Cape Town",
    "eersterivier":     "Cape Town",
    "elsies-river":     "Cape Town",
    "kuils-river":      "Cape Town",
    "mitchells-plain":  "Cape Town",
    "parow":            "Cape Town",
    "strandfontein":    "Cape Town",
    "welcome-glen":     "Cape Town",
    "wellington":       "Cape Town",
    # --- Western Cape: non-metro ---
    "hermanus":         "Hermanus",
    "wilderness":       "Wilderness",
    # --- Eastern Cape ---
    "jeffreys-bay":     "Gqeberha",
    "aberdeen":         "Aberdeen",
    "butterworth":      "Butterworth",
    "mthatha":          "Mthatha",
    # --- Free State ---
    "welkom":           "Welkom",
    "kroonstad":        "Kroonstad",
    # --- North West ---
    "rustenburg":       "Rustenburg",
    "potchefstroom":    "Potchefstroom",
    "klerksdorp":       "Klerksdorp",
    # --- Northern Cape ---
    "kimberley":        "Kimberley",
    "de-aar":           "De Aar",
    "upington":         "Upington",
    # --- Mpumalanga ---
    "delmas":           "Delmas",
    "ermelo":           "Ermelo",
    "white-river":      "White River",
    # --- Limpopo ---
    "lephalale":        "Lephalale",
    "louis-trichardt":  "Louis Trichardt",
    "mookgopong":       "Mookgopong",
    "tzaneen":          "Tzaneen",
}

# Additional towns to query in discovery (not in CITIES).
# Each entry: slug used in Property24 URL, mapped metro, province.
EXTRA_TOWNS = [
    {"slug": s, "name": P24_TOWN_TO_METRO[s],
     "province": next(
         (c["province"] for c in CITIES if c["name"] == P24_TOWN_TO_METRO[s]),
         {"Ekurhuleni": "Gauteng", "Tshwane": "Gauteng",
          "Pietermaritzburg": "KwaZulu-Natal", "George": "Western Cape",
          "Knysna": "Western Cape", "Mossel Bay": "Western Cape",
          "Welkom": "Free State", "Rustenburg": "North West",
          "Potchefstroom": "North West"}.get(P24_TOWN_TO_METRO[s], "Unknown")
     )}
    for s in P24_TOWN_TO_METRO
    if s not in {c["slug"] for c in CITIES}
]
CITY_PROVINCE = {c["name"]: c["province"] for c in CITIES}
CITY_PROVINCE.update({
    "Ekurhuleni":        "Gauteng",
    "Tshwane":           "Gauteng",
    "Pietermaritzburg":  "KwaZulu-Natal",
    "George":            "Western Cape",
    "Knysna":            "Western Cape",
    "Mossel Bay":        "Western Cape",
    "Welkom":            "Free State",
    "Rustenburg":        "North West",
    "Potchefstroom":     "North West",
    # --- Added for unmapped town slugs ---
    "Ladysmith":         "KwaZulu-Natal",
    "Umzimkhulu":        "KwaZulu-Natal",
    "Hermanus":          "Western Cape",
    "Wilderness":        "Western Cape",
    "Aberdeen":          "Eastern Cape",
    "Butterworth":       "Eastern Cape",
    "Mthatha":           "Eastern Cape",
    "Kroonstad":         "Free State",
    "Klerksdorp":        "North West",
    "Kimberley":         "Northern Cape",
    "De Aar":            "Northern Cape",
    "Upington":          "Northern Cape",
    "Delmas":            "Mpumalanga",
    "Ermelo":            "Mpumalanga",
    "White River":       "Mpumalanga",
    "Lephalale":         "Limpopo",
    "Louis Trichardt":   "Limpopo",
    "Mookgopong":        "Limpopo",
    "Tzaneen":           "Limpopo",
})

# ---------------------------------------------------------------------------
# Common Crawl index list (all available as of 2026)
# See: https://index.commoncrawl.org/collinfo.json
# ---------------------------------------------------------------------------
COMMON_CRAWL_INDEXES = [
    "CC-MAIN-2013-20", "CC-MAIN-2014-10", "CC-MAIN-2014-15",
    "CC-MAIN-2014-23", "CC-MAIN-2014-35", "CC-MAIN-2014-41",
    "CC-MAIN-2014-42", "CC-MAIN-2014-49", "CC-MAIN-2014-52",
    "CC-MAIN-2015-06", "CC-MAIN-2015-11", "CC-MAIN-2015-14",
    "CC-MAIN-2015-18", "CC-MAIN-2015-22", "CC-MAIN-2015-27",
    "CC-MAIN-2015-32", "CC-MAIN-2015-35", "CC-MAIN-2015-40",
    "CC-MAIN-2015-48", "CC-MAIN-2016-07", "CC-MAIN-2016-18",
    "CC-MAIN-2016-22", "CC-MAIN-2016-26", "CC-MAIN-2016-30",
    "CC-MAIN-2016-36", "CC-MAIN-2016-40", "CC-MAIN-2016-44",
    "CC-MAIN-2016-50", "CC-MAIN-2017-04", "CC-MAIN-2017-09",
    "CC-MAIN-2017-13", "CC-MAIN-2017-17", "CC-MAIN-2017-22",
    "CC-MAIN-2017-26", "CC-MAIN-2017-30", "CC-MAIN-2017-34",
    "CC-MAIN-2017-39", "CC-MAIN-2017-43", "CC-MAIN-2017-47",
    "CC-MAIN-2017-51", "CC-MAIN-2018-05", "CC-MAIN-2018-09",
    "CC-MAIN-2018-13", "CC-MAIN-2018-17", "CC-MAIN-2018-22",
    "CC-MAIN-2018-26", "CC-MAIN-2018-30", "CC-MAIN-2018-34",
    "CC-MAIN-2018-39", "CC-MAIN-2018-43", "CC-MAIN-2018-47",
    "CC-MAIN-2018-51", "CC-MAIN-2019-04", "CC-MAIN-2019-09",
    "CC-MAIN-2019-13", "CC-MAIN-2019-18", "CC-MAIN-2019-22",
    "CC-MAIN-2019-26", "CC-MAIN-2019-30", "CC-MAIN-2019-35",
    "CC-MAIN-2019-39", "CC-MAIN-2019-43", "CC-MAIN-2019-47",
    "CC-MAIN-2019-51", "CC-MAIN-2020-05", "CC-MAIN-2020-10",
    "CC-MAIN-2020-16", "CC-MAIN-2020-24", "CC-MAIN-2020-29",
    "CC-MAIN-2020-34", "CC-MAIN-2020-40", "CC-MAIN-2020-45",
    "CC-MAIN-2020-50", "CC-MAIN-2021-04", "CC-MAIN-2021-10",
    "CC-MAIN-2021-17", "CC-MAIN-2021-21", "CC-MAIN-2021-25",
    "CC-MAIN-2021-31", "CC-MAIN-2021-39", "CC-MAIN-2021-43",
    "CC-MAIN-2021-49", "CC-MAIN-2022-05", "CC-MAIN-2022-21",
    "CC-MAIN-2022-27", "CC-MAIN-2022-33", "CC-MAIN-2022-40",
    "CC-MAIN-2022-49", "CC-MAIN-2023-06", "CC-MAIN-2023-14",
    "CC-MAIN-2023-23", "CC-MAIN-2023-40", "CC-MAIN-2023-50",
    "CC-MAIN-2024-10", "CC-MAIN-2024-18", "CC-MAIN-2024-26",
    "CC-MAIN-2024-33", "CC-MAIN-2024-38", "CC-MAIN-2024-42",
    "CC-MAIN-2024-46", "CC-MAIN-2024-51", "CC-MAIN-2025-08",
    "CC-MAIN-2025-13", "CC-MAIN-2025-21",
]

# ---------------------------------------------------------------------------
# HTTP headers for polite live scraping
# ---------------------------------------------------------------------------
SCRAPER_CONTACT = "research-scraper/1.0 (academic research; contact: thomasjbrailey@gmail.com)"
