"""
Shared utilities for lead generation pipeline.

Default strategy profile is volume-first:
- keep partially-complete leads when they have enough signal to be useful
- merge duplicate records to preserve the richest combined company profile
- normalize schema differences across sources (for example city vs location)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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

BASE_COMPANY_FIELDS = {
    "company_name",
    "address",
    "city",
    "phone",
    "email",
    "website",
    "company_size",
    "contact_person",
    "source",
    "status",
    "enriched_at",
}


def ensure_dirs():
    """Create necessary directories."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_progress(message: str, source: str = "system"):
    """Log progress to file and console."""
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{source}] {message}"
    print(log_entry)
    with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def log_error(message: str, source: str = "system", exception: Exception = None):
    """Log error to file."""
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    error_entry = f"[{timestamp}] [{source}] {message}"
    if exception:
        error_entry += f"\n  Exception: {str(exception)}"
    print(f"ERROR: {error_entry}")
    with open(ERRORS_LOG, "a", encoding="utf-8") as f:
        f.write(error_entry + "\n")


def load_json(filepath: Path) -> List[Dict]:
    """Load JSON data, return empty list if file doesn't exist."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to load {filepath}", exception=e)
        return []


def save_json(filepath: Path, data: List[Dict], append: bool = False):
    """Save JSON data. If append=True, merge with existing."""
    ensure_dirs()
    if append and filepath.exists():
        existing = load_json(filepath)
        data = existing + data
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log_progress(f"Saved {len(data)} records to {filepath.name}")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_domain(url: str) -> str:
    """Normalize a website into a comparable domain key."""
    cleaned = _clean_text(url)
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
    """Normalize company data while preserving source-specific enrichment fields."""
    normalized = {
        "company_name": _clean_text(company.get("company_name") or company.get("name")),
        "address": _clean_text(company.get("address")),
        "city": _clean_text(company.get("city") or company.get("location")),
        "phone": _clean_text(company.get("phone") or company.get("formatted_phone_number")),
        "email": _clean_text(company.get("email")),
        "website": _clean_text(company.get("website")),
        "company_size": _clean_text(company.get("company_size")),
        "contact_person": _clean_text(company.get("contact_person") or company.get("decision_maker")),
        "source": _clean_text(company.get("source")) or "unknown",
        "status": _clean_text(company.get("status")),
        "enriched_at": _clean_text(company.get("enriched_at")),
    }

    for key, value in company.items():
        if key not in normalized:
            normalized[key] = value

    if "location" not in normalized and normalized["city"]:
        normalized["location"] = normalized["city"]

    return normalized


def validate_company(company: Dict) -> bool:
    """Volume-first validation: keep leads with a company name plus any meaningful location/contact signal."""
    company_name = _clean_text(company.get("company_name"))
    locality_signal = any(
        _clean_text(company.get(field))
        for field in ("city", "location", "address")
    )
    contact_signal = any(
        _clean_text(company.get(field))
        for field in ("phone", "email", "website")
    )
    return bool(company_name and (locality_signal or contact_signal))


def _score_value(field: str, value: Any) -> int:
    """Score a field value so richer records win during merges."""
    if value in (None, "", [], {}):
        return 0
    if isinstance(value, list):
        return len(value) * 5
    if isinstance(value, (int, float)):
        return 5

    text = _clean_text(value)
    if not text:
        return 0

    score = len(text)
    if field in {"email", "phone", "website", "address", "contact_person"}:
        score += 20
    if field in {"company_size", "status", "source"}:
        score += 5
    return score


def _merge_lists(existing: List[Any], incoming: List[Any]) -> List[Any]:
    seen = set()
    merged = []
    for item in existing + incoming:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def merge_company_records(existing: Dict, incoming: Dict) -> Dict:
    """Merge two company records, keeping the richest combined record."""
    left = normalize_company(existing)
    right = normalize_company(incoming)
    merged = dict(left)

    for key, incoming_value in right.items():
        existing_value = merged.get(key)

        if isinstance(existing_value, list) or isinstance(incoming_value, list):
            merged[key] = _merge_lists(existing_value or [], incoming_value or [])
            continue

        if key == "source":
            sources = [s for s in [left.get("source"), right.get("source")] if _clean_text(s)]
            merged[key] = ", ".join(dict.fromkeys(sources)) if sources else "unknown"
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

    if merged.get("additional_emails") and not isinstance(merged["additional_emails"], list):
        merged["additional_emails"] = [merged["additional_emails"]]

    return merged


def company_fingerprints(company: Dict) -> List[str]:
    """Generate matching keys used to merge duplicates without collapsing distinct branches."""
    company_name = _clean_text(company.get("company_name")).lower()
    city = _clean_text(company.get("city") or company.get("location")).lower()
    address = _clean_text(company.get("address")).lower()
    phone = _clean_text(company.get("phone")).lower()
    domain = extract_domain(company.get("website", ""))

    fingerprints: List[str] = []
    if domain:
        fingerprints.append(f"domain:{domain}")
    if company_name and city:
        fingerprints.append(f"name_city:{company_name}|{city}")
    if company_name and address:
        fingerprints.append(f"name_address:{company_name}|{address}")
    if company_name and phone:
        fingerprints.append(f"name_phone:{company_name}|{phone}")
    return fingerprints


def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    """Merge duplicate companies and keep the richest combined record."""
    deduplicated: List[Dict] = []
    fingerprint_to_index: Dict[str, int] = {}

    for raw_company in companies:
        company = normalize_company(raw_company)
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
