#!/usr/bin/env python3
"""
Official volume-first ingestion entrypoint.

Collects leads from supported sources into raw_companies.json using the canonical
schema and preserving source metadata for later enrichment.
"""

import argparse
import json
import os
import time
from typing import Iterable, List

from free_sources_leads import TARGET_CITIES, generate_bootstrap_leads, generate_research_tasks
from google_maps_leads import SEARCH_TERMS, search_google_maps_places
from schema import normalize_lead
from utils import RAW_COMPANIES_FILE, deduplicate_companies, log_error, log_progress, save_json

DEFAULT_CITIES = [city["name"] for city in TARGET_CITIES]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect volume-first lead sources")
    parser.add_argument("--cities", nargs="*", default=DEFAULT_CITIES, help="Cities to search")
    parser.add_argument("--skip-bootstrap", action="store_true", help="Skip bootstrap lead generation")
    parser.add_argument("--with-google-maps", action="store_true", help="Collect from Google Maps API when key is configured")
    parser.add_argument("--with-kompass", action="store_true", help="Collect from Kompass directory")
    parser.add_argument("--kompass-pages", type=int, default=2, help="Pages per city for Kompass")
    parser.add_argument("--pause-ms", type=int, default=250, help="Pause between online source calls")
    return parser.parse_args()


def collect_bootstrap(cities: Iterable[str]) -> List[dict]:
    allowed = set(cities)
    leads = [normalize_lead(lead, source="Bootstrap", source_type="seed") for lead in generate_bootstrap_leads() if lead.get("city") in allowed]
    log_progress(f"Bootstrap collector produced {len(leads)} leads", source="collector")
    return leads


def collect_google_maps(cities: Iterable[str], pause_ms: int) -> List[dict]:
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        log_progress("Skipping Google Maps collection because GOOGLE_MAPS_API_KEY is not set", source="collector")
        return []

    collected: List[dict] = []
    for city in cities:
        for term in SEARCH_TERMS:
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
                    collected.append(normalized)
                log_progress(f"Google Maps collected {len(results)} leads for {term} / {city}", source="collector")
            except Exception as exc:
                log_error(f"Google Maps collection failed for {term} / {city}", source="collector", exception=exc)
            time.sleep(max(pause_ms, 0) / 1000)

    return collected


def collect_kompass(cities: Iterable[str], max_pages: int, pause_ms: int) -> List[dict]:
    from kompass_scraper import search_kompass

    collected: List[dict] = []
    for city in cities:
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
                collected.append(normalized)
            log_progress(f"Kompass collected {len(results)} leads for {city}", source="collector")
        except Exception as exc:
            log_error(f"Kompass collection failed for {city}", source="collector", exception=exc)
        time.sleep(max(pause_ms, 0) / 1000)

    return collected


def main():
    args = parse_args()

    log_progress("Starting official volume-first collection run", source="collector")
    all_leads: List[dict] = []

    if not args.skip_bootstrap:
        all_leads.extend(collect_bootstrap(args.cities))

    if args.with_google_maps:
        all_leads.extend(collect_google_maps(args.cities, args.pause_ms))

    if args.with_kompass:
        all_leads.extend(collect_kompass(args.cities, args.kompass_pages, args.pause_ms))

    deduplicated = deduplicate_companies(all_leads)
    save_json(RAW_COMPANIES_FILE, deduplicated, append=False)

    research_tasks = generate_research_tasks()
    research_tasks["strategy"] = "volume_first"
    research_tasks["cities"] = list(args.cities)
    with open(RAW_COMPANIES_FILE.parent / "research_tasks.json", "w", encoding="utf-8") as f:
        json.dump(research_tasks, f, ensure_ascii=False, indent=2)

    log_progress(f"Collection complete: {len(all_leads)} raw leads -> {len(deduplicated)} unique leads", source="collector")
    print("=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    print(f"Cities: {', '.join(args.cities)}")
    print(f"Collected leads: {len(all_leads)}")
    print(f"Unique leads:    {len(deduplicated)}")
    print(f"Output file:     {RAW_COMPANIES_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
