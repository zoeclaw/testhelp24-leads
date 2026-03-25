"""
Data pipeline: validate, deduplicate, enrich, and output final leads
"""
from typing import List, Dict
from utils import (
    log_progress,
    load_json,
    save_json,
    deduplicate_companies,
    validate_company,
    normalize_company,
    RAW_COMPANIES_FILE,
    ENRICHED_COMPANIES_FILE,
    FINAL_LEADS_FILE,
)


def validate_and_normalize(companies: List[Dict]) -> List[Dict]:
    """Validate and normalize company data"""
    log_progress(f"Validating {len(companies)} companies")
    
    validated = []
    invalid_count = 0
    
    for company in companies:
        normalized = normalize_company(company)
        if validate_company(normalized):
            validated.append(normalized)
        else:
            invalid_count += 1
    
    log_progress(f"Validated: {len(validated)} valid, {invalid_count} invalid")
    return validated


def run_pipeline():
    """
    Execute full pipeline:
    1. Load raw data
    2. Validate & normalize
    3. Deduplicate
    4. Save final leads
    """
    log_progress("Starting pipeline")
    
    # Load raw data
    raw = load_json(RAW_COMPANIES_FILE)
    log_progress(f"Loaded {len(raw)} raw companies")
    
    if not raw:
        log_progress("No raw data to process")
        return
    
    # Validate & normalize
    validated = validate_and_normalize(raw)
    
    # Deduplicate
    deduplicated = deduplicate_companies(validated)
    log_progress(f"After deduplication: {len(deduplicated)} unique companies")
    
    # Save enriched (post-validation, pre-output)
    save_json(ENRICHED_COMPANIES_FILE, deduplicated, append=False)
    
    # Save final output
    save_json(FINAL_LEADS_FILE, deduplicated, append=False)
    
    log_progress(f"Pipeline complete: {len(deduplicated)} final leads")
    
    # Summary stats
    print("\n" + "="*60)
    print("PIPELINE SUMMARY")
    print("="*60)
    print(f"Raw companies:      {len(raw)}")
    print(f"Valid & normalized: {len(validated)}")
    print(f"After dedup:        {len(deduplicated)}")
    print(f"Output file:        {FINAL_LEADS_FILE}")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_pipeline()
