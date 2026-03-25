"""
Kompass.de directory scraper for staffing agencies (lightweight version)
Uses requests + BeautifulSoup instead of Playwright for faster POC
"""
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urlencode
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

# Kompass search endpoint
KOMPASS_SEARCH = "https://www.kompass.de/de/search"

# Headers to avoid being blocked
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def search_kompass(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Search Kompass for staffing agencies in a city
    Returns list of company data
    """
    companies = []
    session = requests.Session()
    session.headers.update(HEADERS)
    
    log_progress(f"Starting Kompass scrape for {city}")
    
    for page_num in range(1, max_pages + 1):
        try:
            # Build search URL
            params = {
                "q": f"Zeitarbeit {city}",
                "page": page_num,
            }
            url = f"{KOMPASS_SEARCH}?{urlencode(params)}"
            
            log_progress(f"Fetching page {page_num}: {url}")
            
            # Fetch page
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find company listings (adjust selectors based on actual Kompass HTML)
            listings = soup.find_all("div", class_="company-result")
            
            if not listings:
                # Try alternative selectors
                listings = soup.find_all("div", {"data-testid": "company-result"})
            
            if not listings:
                # Try yet another selector
                listings = soup.find_all("article", class_="search-result")
            
            if not listings:
                log_progress(f"No listings found on page {page_num}, stopping")
                break
            
            log_progress(f"Found {len(listings)} listings on page {page_num}")
            
            for listing in listings:
                try:
                    # Extract company info
                    name_elem = listing.find("a", class_="company-name")
                    name = name_elem.get_text(strip=True) if name_elem else ""
                    
                    phone_elem = listing.find("span", class_="phone")
                    phone = phone_elem.get_text(strip=True) if phone_elem else ""
                    
                    address_elem = listing.find("span", class_="address")
                    address = address_elem.get_text(strip=True) if address_elem else ""
                    
                    # Try to find link to company page
                    link_elem = listing.find("a", href=True)
                    website = link_elem.get("href", "") if link_elem else ""
                    
                    if name:
                        company_data = {
                            "company_name": name,
                            "address": address,
                            "city": city,
                            "phone": phone,
                            "email": "",
                            "website": website if website.startswith("http") else "",
                            "company_size": "",
                            "contact_person": "",
                            "source": "Kompass",
                        }
                        companies.append(company_data)
                        log_progress(f"  → {name} ({city})")
                
                except Exception as e:
                    log_error(f"Failed to parse listing", source="kompass", exception=e)
                    continue
            
            # Respectful delay between requests
            time.sleep(2)
        
        except Exception as e:
            log_error(f"Error on page {page_num}", source="kompass", exception=e)
            break
    
    return companies


def scrape_city(city: str):
    """Scrape a single city and save results"""
    log_progress(f"=== KOMPASS POC: {city} ===")
    
    companies = search_kompass(city, max_pages=2)  # POC: limit to 2 pages
    
    if companies:
        # Load existing data
        existing = load_json(RAW_COMPANIES_FILE)
        all_companies = existing + companies
        
        # Save incremental
        save_json(RAW_COMPANIES_FILE, all_companies, append=False)
        log_progress(f"✓ POC Kompass complete: {len(companies)} new companies from {city}")
    else:
        log_progress(f"✗ No companies found for {city}")


if __name__ == "__main__":
    # POC: Berlin only
    scrape_city("Berlin")
