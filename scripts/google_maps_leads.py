#!/usr/bin/env python3
"""
Google Maps API lead collector for German staffing agencies.
Produces canonical lead records suitable for volume-first ingestion.
"""

import json
import os
import re
import time
from typing import List

import requests

from schema import make_lead_record
from utils import deduplicate_companies

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

CITIES = [
    "Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt",
    "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig",
    "Dresden", "Hanover", "Nuremberg", "Duisburg", "Bochum",
    "Wuppertal", "Bielefeld", "Bonn", "Mannheim", "Karlsruhe",
    "Augsburg", "Wiesbaden", "Gelsenkirchen", "Potsdam"
]

SEARCH_TERMS = [
    "Zeitarbeit",
    "Personalvermittlung",
    "Staffing Agency"
]


def search_google_maps_places(query: str, location: str) -> list:
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ GOOGLE_MAPS_API_KEY not set. Set environment variable to use Google Maps API.")
        return []

    places = []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{query} {location} Germany",
        "key": GOOGLE_MAPS_API_KEY,
        "language": "de",
        "region": "de"
    }

    try:
        print(f"🔍 Searching: '{query}' in {location}...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            print(f"  ⚠️ API Status: {data.get('status')} - {data.get('error_message', '')}")
            return []

        results = data.get("results", [])
        print(f"  ✓ Found {len(results)} results")

        for result in results:
            place_id = result.get("place_id")
            details = get_place_details(place_id)
            address = details.get("address") or result.get("formatted_address", "")
            lead = make_lead_record(
                company_name=result.get("name", ""),
                address=address,
                city=location,
                location=location,
                phone=details.get("phone", ""),
                website=details.get("website", ""),
                email=extract_email(address),
                source="Google-Maps-API",
                source_type="maps_api",
                google_maps_url=f"https://maps.google.com/?cid={place_id or ''}",
                rating=result.get("rating", ""),
                review_count=result.get("user_ratings_total", 0),
                lead_stage="collected",
                status="collected",
                source_metadata={
                    "query": query,
                    "city": location,
                    "place_id": place_id,
                },
            )
            places.append(lead)
            time.sleep(0.2)

        return places

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {e}")
        return []


def get_place_details(place_id: str) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        return {}

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website,formatted_address",
        "key": GOOGLE_MAPS_API_KEY,
        "language": "de"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            result = data.get("result", {})
            return {
                "phone": result.get("formatted_phone_number", ""),
                "website": result.get("website", ""),
                "address": result.get("formatted_address", "")
            }
    except requests.exceptions.RequestException:
        pass

    return {}


def extract_email(text: str) -> str:
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""


def main():
    print("=" * 60)
    print("🚀 German Staffing Agencies Lead Generation")
    print("=" * 60)
    print()

    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ Note: No API key detected.")
        print("   Set GOOGLE_MAPS_API_KEY environment variable to enable.")
        print("   This script can still be extended with other data sources.")
        print()

    all_leads = []

    for city in CITIES:
        for term in SEARCH_TERMS:
            all_leads.extend(search_google_maps_places(term, city))
            time.sleep(0.5)

    unique_leads = deduplicate_companies(all_leads)
    unique_leads.sort(key=lambda x: x.get("review_count", 0), reverse=True)

    print()
    print("=" * 60)
    print(f"📊 Total Unique Leads: {len(unique_leads)}")
    print("=" * 60)

    output_file = "/home/molt/devspace/testhelp24-leads/data/google_maps_leads.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique_leads, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved to {output_file}")

    print()
    print("Top 10 leads (by review count):")
    print("-" * 60)
    for i, lead in enumerate(unique_leads[:10], 1):
        print(f"{i}. {lead.get('company_name')} ({lead.get('city')})")
        print(f"   📞 {lead.get('phone')}")
        print(f"   🌐 {lead.get('website')}")
        print(f"   ⭐ {lead.get('review_count')} reviews")
        print()


if __name__ == "__main__":
    main()
