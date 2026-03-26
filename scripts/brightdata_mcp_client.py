"""
Brightdata MCP client for web scraping with anti-bot bypass
Communicates with the hosted MCP server using JSON-RPC over HTTP
"""
import requests
import json
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

# Brightdata MCP endpoint
BRIGHTDATA_MCP_ENDPOINT = "https://mcp.brightdata.com/mcp"
BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"

class BrightdataMCPClient:
    """
    Client for Brightdata MCP server
    Uses JSON-RPC over HTTP to call scraping tools
    """
    
    def __init__(self, token: str, endpoint: str = BRIGHTDATA_MCP_ENDPOINT):
        self.token = token
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def scrape_markdown(self, url: str) -> Optional[str]:
        """
        Scrape a URL and return markdown content
        Uses scrape_as_markdown tool
        """
        try:
            log_progress(f"Scraping (MCP): {url}")
            
            # Prepare JSON-RPC request for scrape_as_markdown tool
            # The hosted MCP server handles the request via URL params
            
            params = {
                "token": self.token,
                "url": url,
            }
            
            response = self.session.get(self.endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                # The response should contain HTML/markdown content
                return response.text
            else:
                log_error(f"MCP scrape failed: {response.status_code}", source="mcp_client")
                return None
        
        except Exception as e:
            log_error(f"MCP scrape error", source="mcp_client", exception=e)
            return None
    
    def extract_data(self, url: str, extraction_schema: dict) -> Optional[dict]:
        """
        Extract structured data from URL using MCP extract tool
        extraction_schema: dict describing what to extract
        """
        try:
            log_progress(f"Extracting data (MCP): {url}")
            
            params = {
                "token": self.token,
                "url": url,
                "extract": json.dumps(extraction_schema),
            }
            
            response = self.session.get(self.endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"raw": response.text}
            else:
                log_error(f"MCP extract failed: {response.status_code}", source="mcp_client")
                return None
        
        except Exception as e:
            log_error(f"MCP extract error", source="mcp_client", exception=e)
            return None


def scrape_kompass_with_mcp(city: str, max_pages: int = 3) -> List[Dict]:
    """
    Scrape Kompass using Brightdata MCP with data extraction
    """
    companies = []
    client = BrightdataMCPClient(BRIGHTDATA_TOKEN)
    
    log_progress(f"Scraping Kompass: {city}")
    
    for page_num in range(1, max_pages + 1):
        try:
            url = f"https://de.kompass.com/de/search?q=Zeitarbeit {city}&page={page_num}"
            
            log_progress(f"  Page {page_num}: {url}")
            
            # Scrape page content
            content = client.scrape_markdown(url)
            
            if not content:
                log_progress(f"    Failed to fetch page")
                break
            
            # Parse HTML if markdown extraction didn't work
            soup = BeautifulSoup(content, "html.parser")
            
            # Look for company listings
            listings = soup.select("div[class*='result'], article, div[data-testid*='company']")
            
            if not listings:
                log_progress(f"    No listings found")
                break
            
            log_progress(f"    Found {len(listings)} listings")
            
            for listing in listings:
                try:
                    # Extract company name
                    name_elem = listing.find("a", href=True)
                    name = name_elem.get_text(strip=True) if name_elem else ""
                    
                    if not name:
                        continue
                    
                    # Extract phone
                    phone = ""
                    text_content = listing.get_text(strip=True)
                    
                    # Look for phone pattern
                    import re
                    phone_match = re.search(r'(\+49|0)[0-9\s\-()]{8,}', text_content)
                    if phone_match:
                        phone = phone_match.group(0)
                    
                    company_data = {
                        "company_name": name,
                        "address": text_content[:150],
                        "city": city,
                        "phone": phone,
                        "email": "",
                        "website": name_elem.get("href", "") if name_elem else "",
                        "company_size": "",
                        "contact_person": "",
                        "source": "Kompass-MCP",
                    }
                    companies.append(company_data)
                    log_progress(f"    → {name}")
                
                except Exception as e:
                    log_error(f"Failed to parse listing", source="kompass_mcp", exception=e)
                    continue
            
            time.sleep(2)
        
        except Exception as e:
            log_error(f"Error on page {page_num}", source="kompass_mcp", exception=e)
            break
    
    return companies


def scrape_wlw_with_mcp(city: str) -> List[Dict]:
    """
    Scrape WLW using Brightdata MCP
    """
    companies = []
    client = BrightdataMCPClient(BRIGHTDATA_TOKEN)
    
    log_progress(f"Scraping WLW: {city}")
    
    try:
        url = "https://www.wlw.de/de/de/c/branche/50250200"
        
        log_progress(f"  {url}")
        
        content = client.scrape_markdown(url)
        
        if not content:
            log_progress(f"    Failed to fetch")
            return companies
        
        soup = BeautifulSoup(content, "html.parser")
        
        listings = soup.select("div[class*='result'], article, li[class*='item']")
        
        log_progress(f"    Found {len(listings)} listings")
        
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
                        "source": "WLW-MCP",
                    }
                    companies.append(company_data)
                    log_progress(f"    → {name}")
            
            except Exception as e:
                log_error(f"Failed to parse WLW listing", source="wlw_mcp", exception=e)
                continue
    
    except Exception as e:
        log_error(f"WLW scrape error", source="wlw_mcp", exception=e)
    
    return companies


def scrape_city(city: str):
    """
    Scrape city using Brightdata MCP
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
    scrape_city("Berlin")
