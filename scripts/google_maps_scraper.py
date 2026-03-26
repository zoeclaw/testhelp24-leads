"""
Google Maps API scraper for staffing agencies
Much more reliable than directory scraping for POC
"""
import requests
import json
from typing import List, Dict
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

# Note: You'll need to set GOOGLE_MAPS_API_KEY environment variable
# or pass API key here

PLACES_API_ENDPOINT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_API_ENDPOINT = "https://maps.googleapis.com/maps/api/place/details/json"


def search_google_maps(query: str, api_key: str) -> List[Dict]:
    """
    Search Google Maps for staffing agencies
    Returns raw results
    """
    companies = []
    
    try:
        params = {
            "query": query,
            "key": api_key,
            "language": "de",
        }
        
        log_progress(f"Searching Google Maps: {query}")
        
        response = requests.get(PLACES_API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        log_progress(f"  Found {len(results)} results")
        
        for result in results:
            try:
                company = {
                    "company_name": result.get("name", ""),
                    "address": result.get("formatted_address", ""),
                    "phone": result.get("formatted_phone_number", ""),
                    "website": result.get("website", ""),
                    "google_rating": result.get("rating"),
                    "google_reviews": result.get("user_ratings_total"),
                    "place_id": result.get("place_id", ""),
                    "city": "",
                    "email": "",
                    "company_size": "",
                    "contact_person": "",
                    "source": "Google-Maps",
                }
                
                # Extract city from address
                address_parts = company["address"].split(",")
                if len(address_parts) >= 2:
                    company["city"] = address_parts[-2].strip()
                
                companies.append(company)
                log_progress(f"  → {company['company_name']}")
            
            except Exception as e:
                log_error(f"Failed to parse result", source="google_maps", exception=e)
                continue
        
        # Check for next page token
        next_page_token = data.get("next_page_token")
        if next_page_token:
            log_progress(f"  More results available (pagination not implemented yet)")
        
        return companies
    
    except Exception as e:
        log_error(f"Google Maps search failed", source="google_maps", exception=e)
        return []


def get_place_details(place_id: str, api_key: str) -> Dict:
    """
    Get detailed info for a place (phone, website, hours, etc)
    """
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
        log_error(f"Failed to get place details", source="google_maps", exception=e)
        return {}


def scrape_city_google_maps(city: str, api_key: str = None):
    """
    Scrape a city using Google Maps API
    """
    if not api_key:
        log_error("No Google Maps API key provided", source="google_maps")
        return
    
    log_progress(f"\n{'='*60}")
    log_progress(f"GOOGLE MAPS SEARCH: {city}")
    log_progress(f"{'='*60}")
    
    # Search for staffing agencies
    query = f"Zeitarbeit {city} Germany"
    companies = search_google_maps(query, api_key)
    
    if companies:
        # Load existing
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + companies
        
        # Save
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        log_progress(f"\n✓ Google Maps scraping complete: {len(companies)} companies")
    else:
        log_progress(f"\n✗ No companies found via Google Maps")


if __name__ == "__main__":
    import os
    
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
            log_progress("Using mock data for POC")
            # Create mock data instead
            mock_data = [
                {
                    "company_name": "Zeitarbeit Berlin Center",
                    "address": "Kurfürstendamm 115, 10711 Berlin, Germany",
                    "phone": "+49 30 8849 1100",
                    "website": "https://www.zeitarbeit-berlin.de",
                    "city": "Berlin",
                    "email": "",
                    "company_size": "",
                    "contact_person": "",
                    "source": "Google-Maps-Mock",
                }
            ]
            save_json(RAW_COMPANIES_FILE, mock_data)
            print("✓ Mock data created")
    else:
        scrape_city_google_maps("Berlin", api_key)
