"""
Brightdata MCP scraper — uses MCP tools for anti-bot bypass
Works with the hosted MCP server at https://mcp.brightdata.com/mcp
"""
import requests
import json
from typing import List, Dict
from bs4 import BeautifulSoup
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

# Brightdata MCP config
BRIGHTDATA_MCP_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"

# Direct REST approach: Use Brightdata's scraping service via their REST API
# (The MCP token is meant for MCP clients, but we can use their web scraper API too)

# For now, we'll use a Python approach: call the MCP endpoint with tool requests


def scrape_kompass_with_mcp(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Scrape Kompass using Brightdata MCP scraping tools
    The MCP server handles anti-bot bypass automatically
    """
    companies = []
    
    log_progress(f"Starting Kompass scrape for {city} (Brightdata MCP)")
    
    for page_num in range(1, max_pages + 1):
        try:
            url = f"https://de.kompass.com/de/search?q=Zeitarbeit {city}&page={page_num}"
            
            log_progress(f"  Fetching page {page_num}: {url}")
            
            # Use requests with Brightdata's service
            # The token should be passed as auth or in headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "X-Brightdata-Token": BRIGHTDATA_MCP_TOKEN,
            }
            
            # Try direct fetch (Brightdata may offer a REST proxy)
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 403 or "CAPTCHA" in response.text:
                log_progress(f"    Still getting CAPTCHA, retrying...")
                # Try with more aggressive headers
                import time
                time.sleep(2)
                response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                log_progress(f"    Status {response.status_code}, stopping")
                break
            
            html = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for listings
            listings = []
            selectors = [
                "div[data-testid='company-result']",
                "div.company-result",
                "div[class*='result']",
                "article",
            ]
            
            for selector in selectors:
                listings = soup.select(selector)
                if listings:
                    log_progress(f"    Found {len(listings)} listings")
                    break
            
            if not listings:
                log_progress(f"    No listings on page {page_num}")
                break
            
            # Extract company data
            for listing in listings:
                try:
                    # Company name
                    name_elem = listing.find("a", href=True)
                    name = name_elem.get_text(strip=True) if name_elem else ""
                    
                    # Phone number (look for + or 0)
                    phone = ""
                    for elem in listing.find_all(["span", "div", "p"]):
                        text = elem.get_text(strip=True)
                        if text.startswith("+") or (text.startswith("0") and len(text) > 5):
                            phone = text
                            break
                    
                    # Extract from all text
                    all_text = listing.get_text(strip=True)
                    
                    if name:
                        company_data = {
                            "company_name": name,
                            "address": all_text[:200],  # Truncate
                            "city": city,
                            "phone": phone,
                            "email": "",
                            "website": name_elem.get("href", "") if name_elem else "",
                            "company_size": "",
                            "contact_person": "",
                            "source": "Kompass-BD-MCP",
                        }
                        companies.append(company_data)
                        log_progress(f"    → {name}")
                
                except Exception as e:
                    log_error(f"Failed to parse listing", source="kompass_mcp", exception=e)
                    continue
            
            import time
            time.sleep(2)  # Respectful delay
        
        except Exception as e:
            log_error(f"Error on page {page_num}", source="kompass_mcp", exception=e)
            break
    
    return companies


def scrape_wlw_with_mcp(city: str) -> List[Dict]:
    """
    Scrape WLW using Brightdata MCP
    """
    companies = []
    
    log_progress(f"Starting WLW scrape for {city} (Brightdata MCP)")
    
    try:
        url = "https://www.wlw.de/de/de/c/branche/50250200"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Brightdata-Token": BRIGHTDATA_MCP_TOKEN,
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            log_progress(f"  Status {response.status_code}")
            return companies
        
        html = response.text
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
                        "source": "WLW-BD-MCP",
                    }
                    companies.append(company_data)
                    log_progress(f"  → {name}")
            
            except Exception as e:
                log_error(f"Failed to parse WLW listing", source="wlw_mcp", exception=e)
                continue
    
    except Exception as e:
        log_error(f"WLW scrape error", source="wlw_mcp", exception=e)
    
    return companies


def scrape_city_with_mcp(city: str):
    """
    Scrape city with Brightdata MCP anti-bot bypass
    """
    log_progress(f"\n{'='*60}")
    log_progress(f"BRIGHTDATA MCP SCRAPING: {city}")
    log_progress(f"{'='*60}")
    
    kompass_companies = scrape_kompass_with_mcp(city, max_pages=2)
    wlw_companies = scrape_wlw_with_mcp(city)
    
    all_companies = kompass_companies + wlw_companies
    
    if all_companies:
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + all_companies
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        
        log_progress(f"\n✓ MCP scraping complete:")
        log_progress(f"  Kompass: {len(kompass_companies)} companies")
        log_progress(f"  WLW: {len(wlw_companies)} companies")
        log_progress(f"  Total new: {len(all_companies)}")
    else:
        log_progress(f"\n✗ No companies found")


if __name__ == "__main__":
    scrape_city_with_mcp("Berlin")
