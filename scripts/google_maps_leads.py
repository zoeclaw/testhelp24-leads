#!/usr/bin/env python3
"""
Google Maps API lead scraper for German staffing agencies.
Searches for "Zeitarbeit" (staffing) in major German cities.
No CAPTCHA, no anti-bot protection.
"""

import os
import json
import time
import re
from datetime import datetime
import requests
from urllib.parse import quote

# Google Maps API key (set via environment or hardcode if testing)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Major German cities
CITIES = [
    "Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt",
    "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig",
    "Dresden", "Hanover", "Nuremberg", "Duisburg", "Bochum",
    "Wuppertal", "Bielefeld", "Bonn", "Mannheim", "Karlsruhe",
    "Augsburg", "Wiesbaden", "Gelsenkirchen", "Potsdam"
]

# Search terms for staffing agencies
SEARCH_TERMS = [
    "Zeitarbeit",
    "Personalvermittlung",
    "Staffing Agency"
]

def search_google_maps_places(query: str, location: str) -> list:
    """
    Search Google Maps Places API for staffing agencies.
    Returns list of matching places with contact info.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ GOOGLE_MAPS_API_KEY not set. Set environment variable to use Google Maps API.")
        return []
    
    places = []
    
    # Text search endpoint
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
            name = result.get("name", "")
            address = result.get("formatted_address", "")
            
            # Get detailed info (phone, website, email)
            details = get_place_details(place_id)
            
            place_data = {
                "company_name": name,
                "address": address,
                "phone": details.get("phone", ""),
                "website": details.get("website", ""),
                "email": extract_email(address),
                "google_maps_url": f"https://maps.google.com/?cid={result.get('place_id', '')}",
                "location": location,
                "rating": result.get("rating", ""),
                "review_count": result.get("user_ratings_total", 0),
                "source": "Google-Maps-API"
            }
            
            places.append(place_data)
            time.sleep(0.2)  # Rate limiting
        
        return places
    
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: {e}")
        return []

def get_place_details(place_id: str) -> dict:
    """Get detailed place info from Google Maps Place Details API."""
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
    """Extract email from text if present."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""

def dedup_leads(leads: list) -> list:
    """Remove duplicate entries by company name."""
    seen = set()
    unique = []
    
    for lead in leads:
        name = lead.get("company_name", "").lower().strip()
        if name and name not in seen:
            seen.add(name)
            unique.append(lead)
    
    return unique

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
    
    # Search each city for staffing agencies
    for city in CITIES:
        for term in SEARCH_TERMS:
            results = search_google_maps_places(term, city)
            all_leads.extend(results)
            time.sleep(0.5)  # Rate limiting between requests
    
    # Deduplicate and sort
    unique_leads = dedup_leads(all_leads)
    unique_leads.sort(key=lambda x: x.get("review_count", 0), reverse=True)
    
    print()
    print("=" * 60)
    print(f"📊 Total Unique Leads: {len(unique_leads)}")
    print("=" * 60)
    
    # Save to file
    output_file = "/home/molt/devspace/testhelp24-leads/data/google_maps_leads.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique_leads, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved to {output_file}")
    
    # Print top 10
    print()
    print("Top 10 leads (by review count):")
    print("-" * 60)
    for i, lead in enumerate(unique_leads[:10], 1):
        print(f"{i}. {lead.get('company_name')} ({lead.get('location')})")
        print(f"   📞 {lead.get('phone')}")
        print(f"   🌐 {lead.get('website')}")
        print(f"   ⭐ {lead.get('review_count')} reviews")
        print()

if __name__ == "__main__":
    main()
