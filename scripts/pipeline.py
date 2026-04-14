"""
Data pipeline: validate, normalize, deduplicate, and write canonical leads.
"""

from typing import Dict, List

from schema import count_contact_channels
from utils import (
    ENRICHED_COMPANIES_FILE,
    FINAL_LEADS_FILE,
    RAW_COMPANIES_FILE,
    deduplicate_companies,
    load_json,
    log_progress,
    normalize_company,
    save_json,
    validate_company,
)


def validate_and_normalize(companies: List[Dict]) -> List[Dict]:
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
    log_progress("Starting pipeline")

    raw = load_json(RAW_COMPANIES_FILE)
    log_progress(f"Loaded {len(raw)} raw companies")

    if not raw:
        log_progress("No raw data to process")
        return

    validated = validate_and_normalize(raw)
    deduplicated = deduplicate_companies(validated)
    log_progress(f"After deduplication: {len(deduplicated)} unique companies")

    save_json(ENRICHED_COMPANIES_FILE, deduplicated, append=False)
    save_json(FINAL_LEADS_FILE, deduplicated, append=False)

    contactable = len([company for company in deduplicated if count_contact_channels(company) > 0])
    locality_only = len([company for company in deduplicated if count_contact_channels(company) == 0])

    log_progress(f"Pipeline complete: {len(deduplicated)} final leads")

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Raw companies:      {len(raw)}")
    print(f"Valid & normalized: {len(validated)}")
    print(f"After dedup:        {len(deduplicated)}")
    print(f"Contactable now:    {contactable}")
    print(f"Locality-only:      {locality_only}")
    print(f"Output file:        {FINAL_LEADS_FILE}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_pipeline()
