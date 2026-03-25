"""
Shared utilities for lead generation pipeline
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

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
    """Create necessary directories"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_progress(message: str, source: str = "system"):
    """Log progress to file and console"""
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{source}] {message}"
    print(log_entry)
    with open(PROGRESS_LOG, "a") as f:
        f.write(log_entry + "\n")


def log_error(message: str, source: str = "system", exception: Exception = None):
    """Log error to file"""
    ensure_dirs()
    timestamp = datetime.now().isoformat()
    error_entry = f"[{timestamp}] [{source}] {message}"
    if exception:
        error_entry += f"\n  Exception: {str(exception)}"
    print(f"ERROR: {error_entry}")
    with open(ERRORS_LOG, "a") as f:
        f.write(error_entry + "\n")


def load_json(filepath: Path) -> List[Dict]:
    """Load JSON data, return empty list if file doesn't exist"""
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


def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    """Remove duplicates based on (name, city) and domain"""
    seen = set()
    deduplicated = []
    
    for company in companies:
        # Dedupe by (name, city)
        key = (company.get("company_name", "").lower().strip(), 
               company.get("city", "").lower().strip())
        
        # Also check by domain if website exists
        if company.get("website"):
            domain_key = company.get("website").lower().strip()
            if domain_key in seen:
                continue
            seen.add(domain_key)
        
        if key not in seen:
            seen.add(key)
            deduplicated.append(company)
    
    return deduplicated


def validate_company(company: Dict) -> bool:
    """Validate company has minimum required fields"""
    required = ["company_name", "city"]
    return all(company.get(field, "").strip() for field in required)


def normalize_company(company: Dict) -> Dict:
    """Normalize company data"""
    return {
        "company_name": company.get("company_name", "").strip(),
        "address": company.get("address", "").strip(),
        "city": company.get("city", "").strip(),
        "phone": company.get("phone", "").strip(),
        "email": company.get("email", "").strip(),
        "website": company.get("website", "").strip(),
        "company_size": company.get("company_size", "").strip(),
        "contact_person": company.get("contact_person", "").strip(),
        "source": company.get("source", "").strip(),
    }
