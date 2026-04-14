"""
Shared utilities for the lead generation pipeline.

Volume-first defaults:
- keep partially complete records when they have enough signal to matter
- merge duplicates into the richest combined profile
- normalize all incoming records to the canonical schema
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from schema import clean_text, normalize_lead

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Data files
RAW_COMPANIES_FILE = DATA_DIR / "raw_companies.json"
ENRICHED_COMPANIES_FILE = DATA_DIR / "enriched_companies.json"
FINAL_LEADS_FILE = DATA_DIR / "final_leads.json"

# Logs
PROGRESS_LOG = LOGS_DIR / "progress.log"
ERRORS_LOG = LOGS_DIR / "errors.log"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_progress(message: str, source: str = "system"):
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{source}] {message}"
    print(log_entry)
    with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def log_error(message: str, source: str = "system", exception: Exception = None):
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    error_entry = f"[{timestamp}] [{source}] {message}"
    if exception:
        error_entry += f"\n  Exception: {str(exception)}"
    print(f"ERROR: {error_entry}")
    with open(ERRORS_LOG, "a", encoding="utf-8") as f:
        f.write(error_entry + "\n")


def load_json(filepath: Path) -> List[Dict]:
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        log_error(f"Failed to load {filepath}", exception=e)
        return []


def save_json(filepath: Path, data: List[Dict], append: bool = False):
    ensure_dirs()
    if append and filepath.exists():
        existing = load_json(filepath)
        data = existing + data
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log_progress(f"Saved {len(data)} records to {filepath.name}")


def extract_domain(url: str) -> str:
    cleaned = clean_text(url)
    if not cleaned:
        return ""
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    try:
        parsed = urlparse(cleaned)
        domain = parsed.netloc.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def normalize_company(company: Dict) -> Dict:
    return normalize_lead(company)


def validate_company(company: Dict) -> bool:
    normalized = normalize_company(company)
    company_name = clean_text(normalized.get("company_name"))
    locality_signal = any(clean_text(normalized.get(field)) for field in ("city", "location", "address"))
    contact_signal = any(clean_text(normalized.get(field)) for field in ("phone", "email", "website"))
    return bool(company_name and (locality_signal or contact_signal))


def _score_value(field: str, value: Any) -> int:
    if value in (None, "", [], {}):
        return 0
    if isinstance(value, list):
        return len(value) * 8
    if isinstance(value, dict):
        return len(value) * 4
    if isinstance(value, (int, float)):
        return 5

    text = clean_text(value)
    if not text:
        return 0

    score = len(text)
    if field in {"email", "phone", "website", "address", "contact_person"}:
        score += 20
    if field in {"company_size", "status", "lead_stage", "source", "source_type"}:
        score += 5
    return score


def _merge_lists(existing: List[Any], incoming: List[Any]) -> List[Any]:
    seen = set()
    merged = []
    for item in (existing or []) + (incoming or []):
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def merge_company_records(existing: Dict, incoming: Dict) -> Dict:
    left = normalize_company(existing)
    right = normalize_company(incoming)
    merged = dict(left)

    for key, incoming_value in right.items():
        existing_value = merged.get(key)

        if isinstance(existing_value, list) or isinstance(incoming_value, list):
            merged[key] = _merge_lists(existing_value or [], incoming_value or [])
            continue

        if isinstance(existing_value, dict) or isinstance(incoming_value, dict):
            merged[key] = {**(existing_value or {}), **(incoming_value or {})}
            continue

        if key in {"source", "source_type"}:
            merged_values = []
            for value in [left.get(key), right.get(key)]:
                for part in clean_text(value).split(","):
                    part = clean_text(part)
                    if part and part not in merged_values:
                        merged_values.append(part)
            merged[key] = ", ".join(merged_values) if merged_values else "unknown"
            continue

        if key in {"review_count", "rating"}:
            try:
                merged[key] = max(existing_value or 0, incoming_value or 0)
            except TypeError:
                merged[key] = incoming_value or existing_value
            continue

        if _score_value(key, incoming_value) > _score_value(key, existing_value):
            merged[key] = incoming_value

    if merged.get("city") and not merged.get("location"):
        merged["location"] = merged["city"]

    return normalize_company(merged)


def company_fingerprints(company: Dict) -> List[str]:
    normalized = normalize_company(company)
    company_name = clean_text(normalized.get("company_name")).lower()
    city = clean_text(normalized.get("city") or normalized.get("location")).lower()
    address = clean_text(normalized.get("address")).lower()
    phone = clean_text(normalized.get("phone")).lower()
    domain = extract_domain(normalized.get("website", ""))

    fingerprints: List[str] = []
    if domain and city:
        fingerprints.append(f"domain_city:{domain}|{city}")
    elif domain:
        fingerprints.append(f"domain:{domain}")
    if company_name and city:
        fingerprints.append(f"name_city:{company_name}|{city}")
    if company_name and address:
        fingerprints.append(f"name_address:{company_name}|{address}")
    if company_name and phone:
        fingerprints.append(f"name_phone:{company_name}|{phone}")
    return fingerprints


def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    deduplicated: List[Dict] = []
    fingerprint_to_index: Dict[str, int] = {}

    for raw_company in companies:
        company = normalize_company(raw_company)
        if not validate_company(company):
            continue

        fingerprints = company_fingerprints(company)
        match_index: Optional[int] = None
        for fingerprint in fingerprints:
            if fingerprint in fingerprint_to_index:
                match_index = fingerprint_to_index[fingerprint]
                break

        if match_index is None:
            deduplicated.append(company)
            match_index = len(deduplicated) - 1
        else:
            deduplicated[match_index] = merge_company_records(deduplicated[match_index], company)

        for fingerprint in company_fingerprints(deduplicated[match_index]):
            fingerprint_to_index[fingerprint] = match_index

    return deduplicated
