"""
Kompass.de scraper using Playwright (browser-based)
Handles JavaScript-rendered content and avoids blocking
"""
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

KOMPASS_URL = "https://de.kompass.com/de/search"


def scrape_kompass_browser(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Scrape Kompass using Playwright (browser-based)
    Handles JavaScript rendering and bypasses blocking
    """
    companies = []
    
    with sync_playwright() as p:
        # Launch browser with headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set user agent to appear like real browser
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        try:
            log_progress(f"Starting Kompass scrape for {city} (browser-based)")
            
            for page_num in range(1, max_pages + 1):
                try:
                    # Build URL
                    search_query = f"Zeitarbeit {city}"
                    url = f"{KOMPASS_URL}?q={search_query}&page={page_num}"
                    
                    log_progress(f"Fetching page {page_num}: {url}")
                    
                    # Navigate to page
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for listings to load
                    time.sleep(2)
                    
                    # Extract company listings
                    # Try multiple selectors since Kompass may change structure
                    selectors = [
                        "div[data-testid='company-result']",
                        "div.company-result",
                        "article.search-result",
                        "div.result-item"
                    ]
                    
                    listings = None
                    for selector in selectors:
                        try:
                            listings = page.query_selector_all(selector)
                            if listings:
                                log_progress(f"  Found {len(listings)} listings using selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not listings:
                        log_progress(f"No listings found on page {page_num}, stopping")
                        break
                    
                    # Parse each listing
                    for idx, listing in enumerate(listings):
                        try:
                            # Extract name
                            name_elem = listing.query_selector("a[href*='company']") or listing.query_selector("a")
                            name = name_elem.text_content().strip() if name_elem else ""
                            
                            # Extract contact info
                            phone_elem = listing.query_selector("span:has-text('+')")
                            phone = phone_elem.text_content().strip() if phone_elem else ""
                            
                            address_elem = listing.query_selector("span.address, span.city")
                            address = address_elem.text_content().strip() if address_elem else ""
                            
                            # Try to get company page link
                            link_elem = listing.query_selector("a[href*='company'], a[href*='/de/']")
                            website = link_elem.get_attribute("href") if link_elem else ""
                            
                            if name:
                                company_data = {
                                    "company_name": name,
                                    "address": address,
                                    "city": city,
                                    "phone": phone,
                                    "email": "",
                                    "website": website if website and website.startswith("http") else "",
                                    "company_size": "",
                                    "contact_person": "",
                                    "source": "Kompass-Browser",
                                }
                                companies.append(company_data)
                                log_progress(f"  → {name} ({city})")
                        
                        except Exception as e:
                            log_error(f"Failed to parse listing {idx}", source="kompass_browser", exception=e)
                            continue
                    
                    # Respectful delay between pages
                    time.sleep(3)
                
                except Exception as e:
                    log_error(f"Error on page {page_num}", source="kompass_browser", exception=e)
                    break
        
        finally:
            browser.close()
    
    return companies


def scrape_wlw_browser(city: str, max_pages: int = 2) -> List[Dict]:
    """
    Scrape WLW.de using Playwright (browser-based)
    """
    companies = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        try:
            log_progress(f"Starting WLW scrape for {city} (browser-based)")
            
            # WLW URL for staffing agencies (Branche 50250200 = Zeitarbeit)
            base_url = "https://www.wlw.de/de/de/c/branche/50250200"
            
            for page_num in range(1, max_pages + 1):
                try:
                    url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                    
                    log_progress(f"Fetching WLW page {page_num}: {url}")
                    
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)
                    
                    # Find company listings
                    listings = page.query_selector_all("div[class*='company'], article[class*='result']")
                    
                    if not listings:
                        log_progress(f"No WLW listings found on page {page_num}")
                        break
                    
                    for listing in listings:
                        try:
                            # Extract company info from listing
                            name_elem = listing.query_selector("a, h3, h2")
                            name = name_elem.text_content().strip() if name_elem else ""
                            
                            # Get location/city info
                            location_elem = listing.query_selector("span[class*='location'], span[class*='city']")
                            location = location_elem.text_content().strip() if location_elem else ""
                            
                            if name:
                                company_data = {
                                    "company_name": name,
                                    "address": location,
                                    "city": city,
                                    "phone": "",
                                    "email": "",
                                    "website": "",
                                    "company_size": "",
                                    "contact_person": "",
                                    "source": "WLW-Browser",
                                }
                                companies.append(company_data)
                                log_progress(f"  → {name}")
                        
                        except Exception as e:
                            log_error(f"Failed to parse WLW listing", source="wlw_browser", exception=e)
                            continue
                    
                    time.sleep(3)
                
                except Exception as e:
                    log_error(f"Error on WLW page {page_num}", source="wlw_browser", exception=e)
                    break
        
        finally:
            browser.close()
    
    return companies


def scrape_city(city: str):
    """Scrape both Kompass and WLW for a city"""
    log_progress(f"\n{'='*60}")
    log_progress(f"BROWSER SCRAPING: {city}")
    log_progress(f"{'='*60}")
    
    # Try Kompass
    kompass_companies = scrape_kompass_browser(city, max_pages=2)
    
    # Try WLW
    wlw_companies = scrape_wlw_browser(city, max_pages=1)
    
    all_companies = kompass_companies + wlw_companies
    
    if all_companies:
        # Load existing
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + all_companies
        
        # Save
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        log_progress(f"\n✓ Browser scraping complete:")
        log_progress(f"  Kompass: {len(kompass_companies)} companies")
        log_progress(f"  WLW: {len(wlw_companies)} companies")
        log_progress(f"  Total new: {len(all_companies)}")
    else:
        log_progress(f"\n✗ No companies found via browser scraping")


if __name__ == "__main__":
    # POC: Berlin
    scrape_city("Berlin")
