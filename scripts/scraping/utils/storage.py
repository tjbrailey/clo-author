# ============================================================
# utils/storage.py — Parquet read/write helpers + checkpointing
# ============================================================

import json
import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

# Output schema with dtypes — ensures consistent parquet files across runs
LISTING_SCHEMA = {
    "listing_id":       "string",
    "url":              "string",
    "source":           "string",
    "snapshot_date":    "string",   # stored as ISO date string; cast later
    "publish_date":     "string",
    "city":             "string",
    "suburb":           "string",
    "province":         "string",
    "address_raw":      "string",
    "lat":              "float64",
    "lon":              "float64",
    "price":            "Int64",    # nullable integer
    "property_type":    "string",
    "listing_type":     "string",
    "title":            "string",
    "description":      "string",
    "word_count":       "Int64",
    "psc_flag":         "Int64",
    "psc_score":        "Int64",
    "security_estate":  "Int64",
    "armed_response":   "Int64",
    "boom_gate":        "Int64",
    "access_controlled":"Int64",
    "electric_fence":   "Int64",
    "psc_companies":    "string",
    "geocode_source":   "string",
}


def empty_listing() -> dict:
    """Return an empty record with all schema fields set to None."""
    return {k: None for k in LISTING_SCHEMA}


def save_parquet(records: list[dict], path: Path, append: bool = False) -> int:
    """
    Save records to parquet. If append=True and file exists, concatenate.
    Returns total record count in file.
    """
    if not records:
        logger.warning("save_parquet called with empty records list")
        return 0

    df = pd.DataFrame(records)
    # Ensure all schema columns exist
    for col, dtype in LISTING_SCHEMA.items():
        if col not in df.columns:
            df[col] = None
        try:
            df[col] = df[col].astype(dtype)
        except (ValueError, TypeError):
            pass  # keep original type on cast failure

    if append and path.exists():
        existing = pd.read_parquet(path)
        df = pd.concat([existing, df], ignore_index=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(df)} records to {path}")
    return len(df)


def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        logger.warning(f"Parquet file not found: {path}")
        return pd.DataFrame(columns=list(LISTING_SCHEMA.keys()))
    return pd.read_parquet(path)


def load_checkpoint(checkpoint_path: Path) -> set:
    """Load set of already-processed URLs from checkpoint file."""
    if not checkpoint_path.exists():
        return set()
    with open(checkpoint_path) as f:
        return set(line.strip() for line in f if line.strip())


def save_checkpoint(url: str, checkpoint_path: Path):
    """Append a URL to the checkpoint file."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "a") as f:
        f.write(url + "\n")


def append_jsonl(record: dict, path: Path):
    """Append a single JSON record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    """Load all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records
