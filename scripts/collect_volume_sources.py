#!/usr/bin/env python3
"""
Official volume-first ingestion entrypoint.

Collects leads from supported sources into raw_companies.json using the canonical
schema and preserving source metadata for later enrichment.

Default behavior is resume-safe:
- existing raw leads are loaded first
- new batches are merged into them
- progress is checkpointed after each source batch

So if a run is stopped and restarted, we append/merge instead of losing prior work.
"""

import argparse
import json
import os
import time
from typing import Iterable, List

from free_sources_leads import TARGET_CITIES, generate_bootstrap_leads, generate_research_tasks
from google_maps_leads import SEARCH_TERMS, search_google_maps_places
from schema import normalize_lead
from utils import RAW_COMPANIES_FILE, deduplicate_companies, load_json, log_error, log_progress, save_json

DEFAULT_CITIES = [city["name"] for city in TARGET_CITIES]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect volume-first lead sources")
    parser.add_argument("--cities", nargs="*", default=DEFAULT_CITIES, help="Cities to search")
    parser.add_argument("--skip-bootstrap", action="store_true", help="Skip bootstrap lead generation")
    parser.add_argument("--with-google-maps", action="store_true", help="Collect from Google Maps API when key is configured")
    parser.add_argument("--with-kompass", action="store_true", help="Collect from Kompass directory")
    parser.add_argument("--kompass-pages", type=int, default=2, help="Pages per city for Kompass")
    parser.add_argument("--pause-ms", type=int, default=250, help="Pause between online source calls")
    parser.add_argument("--fresh-start", action="store_true", help="Ignore existing raw_companies.json and rebuild from scratch")
    return parser.parse_args()


def collect_bootstrap(cities: Iterable[str]) -> List[dict]:
    allowed = set(cities)
    leads = [
        normalize_lead(lead, source="Bootstrap", source_type="seed")
        for lead in generate_bootstrap_leads()
        if lead.get("city") in allowed
    ]
    log_progress(f"Bootstrap collector produced {len(leads)} leads", source="collector")
    return leads


def merge_and_checkpoint(existing: List[dict], new_leads: List[dict], label: str) -> List[dict]:
    if not new_leads:
        log_progress(f"No new leads from {label}", source="collector")
        return existing

    merged = deduplicate_companies(existing + new_leads)
    save_json(RAW_COMPANIES_FILE, merged, append=False)
    log_progress(
        f"Checkpoint after {label}: +{len(new_leads)} leads, {len(merged)} unique total",
        source="collector",
    )
    return merged


def collect_google_maps(existing: List[dict], cities: Iterable[str], pause_ms: int) -> List[dict]:
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        log_progress("Skipping Google Maps collection because GOOGLE_MAPS_API_KEY is not set", source="collector")
        return existing

    for city in cities:
        for term in SEARCH_TERMS:
            batch: List[dict] = []
            try:
                results = search_google_maps_places(term, city)
                for lead in results:
                    normalized = normalize_lead(lead, source="Google-Maps-API", source_type="maps_api")
                    normalized["lead_stage"] = "collected"
                    normalized.setdefault("source_metadata", {})
                    normalized["source_metadata"].update({
                        "query": term,
                        "city": city,
                    })
                    batch.append(normalized)
                log_progress(f"Google Maps collected {len(results)} leads for {term} / {city}", source="collector")
            except Exception as exc:
                log_error(f"Google Maps collection failed for {term} / {city}", source="collector", exception=exc)

            existing = merge_and_checkpoint(existing, batch, f"Google Maps {term} / {city}")
            time.sleep(max(pause_ms, 0) / 1000)

    return existing


def collect_kompass(existing: List[dict], cities: Iterable[str], max_pages: int, pause_ms: int) -> List[dict]:
    from kompass_scraper import search_kompass

    for city in cities:
        batch: List[dict] = []
        try:
            results = search_kompass(city, max_pages=max_pages)
            for lead in results:
                normalized = normalize_lead(lead, source="Kompass", source_type="directory")
                normalized["lead_stage"] = "collected"
                normalized.setdefault("source_metadata", {})
                normalized["source_metadata"].update({
                    "city": city,
                    "pages_requested": max_pages,
                })
                batch.append(normalized)
            log_progress(f"Kompass collected {len(results)} leads for {city}", source="collector")
        except Exception as exc:
            log_error(f"Kompass collection failed for {city}", source="collector", exception=exc)

        existing = merge_and_checkpoint(existing, batch, f"Kompass {city}")
        time.sleep(max(pause_ms, 0) / 1000)

    return existing


def main():
    args = parse_args()

    log_progress("Starting official volume-first collection run", source="collector")
    existing_leads: List[dict] = [] if args.fresh_start else load_json(RAW_COMPANIES_FILE)
    if args.fresh_start:
        log_progress("Fresh start requested: ignoring existing raw leads", source="collector")
    else:
        log_progress(f"Loaded {len(existing_leads)} existing raw leads for append/merge", source="collector")

    starting_count = len(existing_leads)
    current_leads = existing_leads

    if not args.skip_bootstrap:
        current_leads = merge_and_checkpoint(current_leads, collect_bootstrap(args.cities), "bootstrap")

    if args.with_google_maps:
        current_leads = collect_google_maps(current_leads, args.cities, args.pause_ms)

    if args.with_kompass:
        current_leads = collect_kompass(current_leads, args.cities, args.kompass_pages, args.pause_ms)

    research_tasks = generate_research_tasks()
    research_tasks["strategy"] = "volume_first"
    research_tasks["cities"] = list(args.cities)
    with open(RAW_COMPANIES_FILE.parent / "research_tasks.json", "w", encoding="utf-8") as f:
        json.dump(research_tasks, f, ensure_ascii=False, indent=2)

    added_count = max(0, len(current_leads) - starting_count)
    log_progress(
        f"Collection complete: started with {starting_count}, ended with {len(current_leads)} unique leads, net +{added_count}",
        source="collector",
    )
    print("=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"Cities: {', '.join(args.cities)}")
    print(f"Started with: {starting_count}")
    print(f"Ended with:   {len(current_leads)}")
    print(f"Net added:    {added_count}")
    print(f"Output file:  {RAW_COMPANIES_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
