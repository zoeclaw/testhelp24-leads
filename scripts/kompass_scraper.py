"""
Kompass.de directory scraper for staffing agencies
"""
import time
import json
from typing import List, Dict
from urllib.parse import urlencode
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Kompass search endpoint
KOMPASS_BASE = "https://www.kompass.de"
KOMPASS_SEARCH = f"{KOMPASS_BASE}/de/search"


def search_kompass(city: str, max_pages: int = 5) -> List[Dict]:
    """
    Search Kompass for staffing agencies in a city
    Returns list of company data
    """
    companies = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Kompass query: Zeitarbeit (staffing) in city
            params = {
                "q": f"Zeitarbeit {city}",
                "sector": "",
            }
            url = f"{KOMPASS_SEARCH}?{urlencode(params)}"
            
            log_progress(f"Scraping Kompass: {city}")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(2)  # Let JS load
            
            for page_num in range(1, max_pages + 1):
                try:
                    # Look for company listings
                    listings = page.locator("div[data-testid='company-result']")
                    count = listings.count()
                    
                    if count == 0:
                        log_progress(f"No more results on page {page_num}")
                        break
                    
                    log_progress(f"Found {count} companies on page {page_num}")
                    
                    for i in range(count):
                        try:
                            listing = listings.nth(i)
                            
                            # Extract data from listing
                            company_data = {
                                "company_name": listing.locator("a[data-testid='company-name']").inner_text() if listing.locator("a[data-testid='company-name']").count() > 0 else "",
                                "address": listing.locator("span[data-testid='address']").inner_text() if listing.locator("span[data-testid='address']").count() > 0 else "",
                                "city": city,
                                "phone": listing.locator("span[data-testid='phone']").inner_text() if listing.locator("span[data-testid='phone']").count() > 0 else "",
                                "email": "",  # Will enrich later
                                "website": "",  # Will enrich later
                                "company_size": "",
                                "contact_person": "",
                                "source": "Kompass",
                            }
                            
                            if company_data["company_name"]:
                                companies.append(company_data)
                        
                        except Exception as e:
                            log_error(f"Failed to extract listing {i}", source="kompass", exception=e)
                            continue
                    
                    # Try to go to next page
                    next_button = page.locator("a[aria-label*='next']")
                    if next_button.count() > 0:
                        next_button.click()
                        time.sleep(2)
                    else:
                        log_progress(f"No next page button found, stopping at page {page_num}")
                        break
                
                except Exception as e:
                    log_error(f"Error on page {page_num}", source="kompass", exception=e)
                    break
            
            browser.close()
    
    except Exception as e:
        log_error(f"Kompass scraper failed for {city}", source="kompass", exception=e)
    
    return companies


def scrape_city(city: str):
    """Scrape a single city and save results"""
    log_progress(f"Starting Kompass POC for {city}")
    
    companies = search_kompass(city, max_pages=3)  # POC: limit to 3 pages
    
    if companies:
        # Load existing data
        existing = load_json(RAW_COMPANIES_FILE)
        all_companies = existing + companies
        
        # Save incremental
        save_json(RAW_COMPANIES_FILE, all_companies, append=False)
        log_progress(f"POC complete: {len(companies)} new companies from Kompass ({city})")
    else:
        log_progress(f"No companies found for {city}")


if __name__ == "__main__":
    # POC: Berlin only
    scrape_city("Berlin")
