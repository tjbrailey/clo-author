---
name: scrape
description: Property listing scraper for PSC/gated community research. Three modes: archive (Common Crawl + Wayback Machine), live (polite rate-limited), classify (PSC keyword extraction). Produces parquet datasets for spatial merge with Afrobarometer.
argument-hint: "[target] [--mode archive|live|classify] [--city CITY] [--limit N] [--input FILE]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Task
---

# Scrape

Collect property listing data from Property24 for PSC/gated community treatment variable construction.

**Input:** `$ARGUMENTS` — target site and mode flags.

**Modes:**
- `property24 --mode archive` — historical panel via Common Crawl + Wayback Machine (safe, no live requests to Property24)
- `property24 --mode live [--limit N]` — polite live scraping for current listings (default limit: 200 requests)
- `--classify [file]` — run PSC keyword classification on an existing listings parquet

---

## Safety Rules (MANDATORY — check before every run)

1. **Archive mode:** Never send requests directly to property24.com. Use CDX APIs and Wayback Machine only.
2. **Live mode:** Check `robots.txt` at start. Fail hard if path is disallowed. Minimum 10s delay between requests (randomized 10–30s). Hard stop on HTTP 429 or 3 consecutive errors.
3. **Live mode:** Max 200 requests per session unless `--limit` explicitly overrides.
4. **All output:** Write to `data/raw/scraping/` (gitignored). Never overwrite existing parquet without confirmation.
5. **Rate limits:** Wayback CDX API ≤ 0.5 req/sec. Common Crawl CDX API ≤ 1 req/sec. Nominatim geocoding ≤ 1 req/sec.
6. **Checkpoint:** Save progress every 500 records. Script must be safely re-runnable (skip already-fetched URLs).

---

## Workflow

### Step 1: Validate environment

```bash
cd scripts/scraping && pip3 install -r requirements.txt --quiet
```

Check that output directories exist:
```
data/raw/scraping/
data/cleaned/
```

### Step 2: Route by mode

**If `--mode archive` (or no mode specified):**
→ Run Steps 3–4

**If `--mode live`:**
→ Run Step 5

**If `--classify [file]`:**
→ Jump to Step 6

### Step 3: Archive discovery (CDX APIs)

Run `scripts/scraping/00_archive_discovery.py`:
```bash
python3 scripts/scraping/00_archive_discovery.py \
  [--city CITY_SLUG]   \   # e.g. johannesburg (omit for all cities)
  [--limit N]              # max URLs per city (default: unlimited)
```

This queries:
- Common Crawl CDX: all indexes from 2013–present for `property24.com/for-sale/*` and `property24.com/to-rent/*`
- Wayback Machine CDX: same URL patterns

Output: `data/raw/scraping/url_inventory.jsonl` — one record per URL+timestamp pair.

Report: number of unique listing URLs found, breakdown by city and year.

### Step 4: Archive fetch + parse

Run `scripts/scraping/01_archive_fetch.py`:
```bash
python3 scripts/scraping/01_archive_fetch.py \
  [--source wayback|commoncrawl]  \  # default: wayback (simpler)
  [--year YYYY]                    \  # process one year at a time
  [--limit N]                          # max records (useful for testing)
```

Output: `data/raw/scraping/listings_archive_YYYY.parquet` per year.

Parsing priority order:
1. JSON-LD (`<script type="application/ld+json">`) — most reliable
2. OpenGraph meta tags
3. HTML selectors (fallback for older archive pages)

Report: records fetched, parse success rate, fields with high null rate.

### Step 5: Live scraping (if `--mode live`)

Run `scripts/scraping/02_live_scraper.py`:
```bash
python3 scripts/scraping/02_live_scraper.py \
  [--city CITY_SLUG]    \   # e.g. cape-town
  [--limit N]               # default: 200
```

Sequence:
1. Check `robots.txt` — abort if `/for-sale/` or `/to-rent/` is disallowed
2. Fetch search result page → extract listing URLs
3. For each listing URL: random sleep(10, 30) → fetch → parse
4. On HTTP 429: back off 5 minutes, retry once, then stop
5. Checkpoint every 50 records

Output: `data/raw/scraping/listings_live_YYYYMMDD.parquet`

### Step 6: PSC classification

Run `scripts/scraping/04_classify_psc.py`:
```bash
python3 scripts/scraping/04_classify_psc.py \
  --input data/raw/scraping/listings_all.parquet   \   # or specify a file
  --output data/raw/scraping/listings_classified.parquet
```

Adds columns:
- `psc_flag` — 1 if any PSC indicator present
- `security_estate` — gated/security estate language
- `armed_response` — armed response / armed guard
- `boom_gate` — boom gate / boom controlled / access boom
- `access_controlled` — access controlled / access control
- `electric_fence` — electric fence / electrified perimeter
- `psc_companies` — pipe-separated PSC company names found (ADT, Fidelity, G4S, etc.)
- `psc_score` — total keyword hits

Report: distribution of `psc_score`, share of listings with `psc_flag=1` by city and year.

### Step 7: Geocoding (if needed)

Run `scripts/scraping/05_geocode.py`:
```bash
python3 scripts/scraping/05_geocode.py \
  --input data/raw/scraping/listings_classified.parquet \
  --output data/cleaned/listings_geocoded.parquet
```

Uses Nominatim (OpenStreetMap). Rate: 1 req/sec. Caches results to avoid re-querying.

Output: final parquet with `lat`, `lon`, `geocode_source` columns added.

### Step 8: Present results

Report to user:
1. **Records collected** — total, by source (archive/live), by city, by year
2. **PSC statistics** — share `psc_flag=1`, top PSC companies, distribution of `psc_score`
3. **Coverage map** — which Afrobarometer waves overlap with which archive years
4. **Data quality flags** — null rate on key fields (description, publish_date, suburb)
5. **Next steps** — suggest geocoding if not done; suggest merging with Afrobarometer

---

## Output Schema (all parquet files)

| Field | Type | Notes |
|-------|------|-------|
| `listing_id` | str | MD5 of canonical URL |
| `url` | str | Source URL |
| `source` | str | `common_crawl`, `wayback`, `live` |
| `snapshot_date` | date | Archive date or fetch date |
| `publish_date` | date | Date listing was posted |
| `city` | str | Standardized city name |
| `suburb` | str | Raw suburb string |
| `province` | str | Standardized province |
| `address_raw` | str | Full address string |
| `lat` | float | Geocoded (after Stage 5) |
| `lon` | float | Geocoded (after Stage 5) |
| `price` | int | ZAR (nullable) |
| `property_type` | str | house, apartment, townhouse, estate |
| `listing_type` | str | for_sale, to_rent |
| `title` | str | Listing title |
| `description` | str | Full description text |
| `word_count` | int | Description length |
| `psc_flag` | int | 1 if any PSC indicator (after Stage 6) |
| `psc_score` | int | Count of keyword hits |
| `security_estate` | int | 0/1 flag |
| `armed_response` | int | 0/1 flag |
| `boom_gate` | int | 0/1 flag |
| `access_controlled` | int | 0/1 flag |
| `electric_fence` | int | 0/1 flag |
| `psc_companies` | str | Pipe-separated company names |

---

## Principles

- **Archive first.** Never send requests to Property24 when archive data is available.
- **Polite live scraping.** 10–30s random delay always. Not negotiable.
- **Checkpoint everything.** Scripts must survive interruption and resume cleanly.
- **No hardcoded paths.** All paths from `config.py` or CLI args.
- **Parquet only.** Never output CSV for large datasets — parquet preserves types and compresses well.
- **Classify separately.** Classification is a post-hoc step that can be re-run with improved keyword lists.
