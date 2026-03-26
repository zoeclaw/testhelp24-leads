"""
Brightdata MCP scraper for Kompass and WLW
Uses Brightdata's anti-bot bypass to get around CAPTCHA
"""
import requests
import json
from typing import List, Dict
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE
from bs4 import BeautifulSoup

# Brightdata MCP endpoint
BRIGHTDATA_MCP = "https://mcp.brightdata.com/mcp"
BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_with_brightdata(url: str) -> str:
    """
    Fetch URL through Brightdata's anti-bot bypass
    Returns HTML content
    """
    try:
        # Use Brightdata's MCP to fetch the page
        params = {
            "token": BRIGHTDATA_TOKEN,
            "groups": "advanced_scraping",
            "url": url,
        }
        
        log_progress(f"Fetching via Brightdata: {url}")
        
        response = requests.get(BRIGHTDATA_MCP, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        return response.text
    
    except Exception as e:
        log_error(f"Brightdata fetch failed", source="brightdata", exception=e)
        return None


def scrape_kompass_brightdata(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Scrape Kompass using Brightdata to bypass CAPTCHA
    """
    companies = []
    
    log_progress(f"Starting Kompass scrape for {city} (Brightdata)")
    
    for page_num in range(1, max_pages + 1):
        try:
            url = f"https://de.kompass.com/de/search?q=Zeitarbeit {city}&page={page_num}"
            
            # Fetch HTML via Brightdata
            html = fetch_with_brightdata(url)
            
            if not html:
                log_progress(f"Failed to fetch page {page_num}")
                break
            
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for company listings (try multiple selectors)
            listings = []
            selectors = [
                "div[data-testid='company-result']",
                "div.company-result",
                "article.search-result",
                "div.kompass-result",
                "div[class*='result']",
            ]
            
            for selector in selectors:
                listings = soup.select(selector)
                if listings:
                    log_progress(f"  Found {len(listings)} listings using selector: {selector}")
                    break
            
            if not listings:
                log_progress(f"No listings found on page {page_num}")
                break
            
            # Extract company info
            for listing in listings:
                try:
                    # Try to extract name
                    name_elem = listing.find("a", href=True)
                    name = name_elem.get_text(strip=True) if name_elem else ""
                    
                    # Phone
                    phone_elems = listing.find_all("span")
                    phone = ""
                    for span in phone_elems:
                        text = span.get_text(strip=True)
                        if text.startswith("+") or text.startswith("0"):
                            phone = text
                            break
                    
                    # Address/city
                    address_text = listing.get_text(strip=True)
                    
                    if name:
                        company_data = {
                            "company_name": name,
                            "address": address_text[:200],  # Truncate
                            "city": city,
                            "phone": phone,
                            "email": "",
                            "website": name_elem.get("href", "") if name_elem else "",
                            "company_size": "",
                            "contact_person": "",
                            "source": "Kompass-Brightdata",
                        }
                        companies.append(company_data)
                        log_progress(f"  → {name}")
                
                except Exception as e:
                    log_error(f"Failed to parse listing", source="kompass_brightdata", exception=e)
                    continue
        
        except Exception as e:
            log_error(f"Error on page {page_num}", source="kompass_brightdata", exception=e)
            break
    
    return companies


def scrape_wlw_brightdata(city: str, max_pages: int = 2) -> List[Dict]:
    """
    Scrape WLW using Brightdata
    """
    companies = []
    
    log_progress(f"Starting WLW scrape for {city} (Brightdata)")
    
    try:
        url = "https://www.wlw.de/de/de/c/branche/50250200"
        
        # Fetch via Brightdata
        html = fetch_with_brightdata(url)
        
        if not html:
            log_progress("Failed to fetch WLW")
            return companies
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Find listings
        listings = soup.select("div[class*='result'], article, li[class*='item']")
        
        log_progress(f"  Found {len(listings)} potential listings")
        
        for listing in listings:
            try:
                name_elem = listing.find("a")
                name = name_elem.get_text(strip=True) if name_elem else ""
                
                if name and len(name) > 3:
                    company_data = {
                        "company_name": name,
                        "address": "",
                        "city": city,
                        "phone": "",
                        "email": "",
                        "website": name_elem.get("href", "") if name_elem else "",
                        "company_size": "",
                        "contact_person": "",
                        "source": "WLW-Brightdata",
                    }
                    companies.append(company_data)
                    log_progress(f"  → {name}")
            
            except Exception as e:
                log_error(f"Failed to parse WLW listing", source="wlw_brightdata", exception=e)
                continue
    
    except Exception as e:
        log_error(f"WLW scrape error", source="wlw_brightdata", exception=e)
    
    return companies


def scrape_city_brightdata(city: str):
    """
    Scrape both Kompass and WLW for a city using Brightdata
    """
    log_progress(f"\n{'='*60}")
    log_progress(f"BRIGHTDATA SCRAPING: {city}")
    log_progress(f"{'='*60}")
    
    # Scrape Kompass
    kompass_companies = scrape_kompass_brightdata(city, max_pages=2)
    
    # Scrape WLW
    wlw_companies = scrape_wlw_brightdata(city, max_pages=1)
    
    all_companies = kompass_companies + wlw_companies
    
    if all_companies:
        # Load existing
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + all_companies
        
        # Save
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        log_progress(f"\n✓ Brightdata scraping complete:")
        log_progress(f"  Kompass: {len(kompass_companies)} companies")
        log_progress(f"  WLW: {len(wlw_companies)} companies")
        log_progress(f"  Total new: {len(all_companies)}")
    else:
        log_progress(f"\n✗ No companies found")


if __name__ == "__main__":
    # Test with Berlin
    scrape_city_brightdata("Berlin")
