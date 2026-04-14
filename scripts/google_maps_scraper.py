"""
Legacy Google Maps API scraper for staffing agencies.
Kept for compatibility, but now emits canonical lead records.
"""

import os
from typing import Dict, List

import requests

from schema import make_lead_record
from utils import RAW_COMPANIES_FILE, load_json, log_error, log_progress, save_json

PLACES_API_ENDPOINT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_API_ENDPOINT = "https://maps.googleapis.com/maps/api/place/details/json"


def search_google_maps(query: str, api_key: str) -> List[Dict]:
    companies = []

    try:
        params = {
            "query": query,
            "key": api_key,
            "language": "de",
        }

        log_progress(f"Searching Google Maps: {query}", source="google_maps")

        response = requests.get(PLACES_API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        log_progress(f"Found {len(results)} results", source="google_maps")

        for result in results:
            try:
                address = result.get("formatted_address", "")
                city = ""
                address_parts = [part.strip() for part in address.split(",") if part.strip()]
                if len(address_parts) >= 2:
                    city = address_parts[-2]

                company = make_lead_record(
                    company_name=result.get("name", ""),
                    address=address,
                    city=city,
                    location=city,
                    phone=result.get("formatted_phone_number", ""),
                    website=result.get("website", ""),
                    source="Google-Maps",
                    source_type="maps_api",
                    rating=result.get("rating"),
                    review_count=result.get("user_ratings_total"),
                    place_id=result.get("place_id", ""),
                    lead_stage="collected",
                    status="collected",
                )

                companies.append(company)
                log_progress(f"→ {company['company_name']}", source="google_maps")

            except Exception as e:
                log_error("Failed to parse result", source="google_maps", exception=e)
                continue

        next_page_token = data.get("next_page_token")
        if next_page_token:
            log_progress("More results available (pagination not implemented yet)", source="google_maps")

        return companies

    except Exception as e:
        log_error("Google Maps search failed", source="google_maps", exception=e)
        return []


def get_place_details(place_id: str, api_key: str) -> Dict:
    try:
        params = {
            "place_id": place_id,
            "key": api_key,
            "language": "de",
            "fields": "name,formatted_phone_number,website,opening_hours,address_components"
        }

        response = requests.get(DETAILS_API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return data.get("result", {})

    except Exception as e:
        log_error("Failed to get place details", source="google_maps", exception=e)
        return {}


def scrape_city_google_maps(city: str, api_key: str = None):
    if not api_key:
        log_error("No Google Maps API key provided", source="google_maps")
        return

    log_progress(f"\n{'=' * 60}", source="google_maps")
    log_progress(f"GOOGLE MAPS SEARCH: {city}", source="google_maps")
    log_progress(f"{'=' * 60}", source="google_maps")

    query = f"Zeitarbeit {city} Germany"
    companies = search_google_maps(query, api_key)

    if companies:
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + companies
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        log_progress(f"✓ Google Maps scraping complete: {len(companies)} companies", source="google_maps")
    else:
        log_progress("✗ No companies found via Google Maps", source="google_maps")


if __name__ == "__main__":
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        print("⚠️  No GOOGLE_MAPS_API_KEY set. To use Google Maps scraper:")
        print("   1. Create a Google Cloud project")
        print("   2. Enable Places API")
        print("   3. Generate API key")
        print("   4. Set: export GOOGLE_MAPS_API_KEY=your_key")
        print("\n   For POC testing, set DEMO=1 to use mock data")

        demo = os.getenv("DEMO")
        if demo:
            log_progress("Using mock data for POC", source="google_maps")
            mock_data = [
                make_lead_record(
                    company_name="Zeitarbeit Berlin Center",
                    address="Kurfürstendamm 115, 10711 Berlin, Germany",
                    phone="+49 30 8849 1100",
                    website="https://www.zeitarbeit-berlin.de",
                    city="Berlin",
                    location="Berlin",
                    source="Google-Maps-Mock",
                    source_type="mock",
                    lead_stage="collected",
                    status="collected",
                )
            ]
            save_json(RAW_COMPANIES_FILE, mock_data)
            print("✓ Mock data created")
    else:
        scrape_city_google_maps("Berlin", api_key)
