#!/usr/bin/env python3
"""
Lead enrichment script - adds contact details, validates websites, finds emails.
Combines bootstrap data with enrichment from web sources.
"""

import os
import json
import time
import re
import requests
from datetime import datetime
from typing import Optional

class LeadEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.enriched_count = 0
        self.failed_count = 0
    
    def find_emails_from_website(self, website: str) -> list:
        """Scrape website for email addresses."""
        if not website or not website.startswith('http'):
            return []
        
        emails = []
        try:
            response = self.session.get(website, timeout=5)
            response.encoding = 'utf-8'
            
            # Extract all emails from page
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            found_emails = re.findall(email_pattern, response.text)
            
            # Filter for relevant addresses (info, kontakt, sales, etc.)
            relevant_keywords = ['info', 'kontakt', 'hello', 'sales', 'recruitment', 'hr', 'jobs', 'careers', 'contact']
            for email in set(found_emails):
                local_part = email.split('@')[0].lower()
                if any(keyword in local_part for keyword in relevant_keywords):
                    emails.append(email)
            
            return list(set(emails))[:3]  # Return top 3 unique emails
        
        except requests.exceptions.RequestException:
            return []
    
    def validate_website(self, website: str) -> bool:
        """Check if website is accessible."""
        if not website or not website.startswith('http'):
            return False
        
        try:
            response = self.session.head(website, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except requests.exceptions.RequestException:
            return False
    
    def enrich_lead(self, lead: dict) -> dict:
        """Enrich a single lead with additional data."""
        try:
            # Validate/fix website
            if lead.get('website'):
                if not lead['website'].startswith('http'):
                    lead['website'] = f"https://{lead['website']}"
                
                if self.validate_website(lead['website']):
                    # Try to find emails on website
                    emails = self.find_emails_from_website(lead['website'])
                    if emails and not lead.get('email'):
                        lead['email'] = emails[0]
                        if len(emails) > 1:
                            lead['additional_emails'] = emails[1:]
                else:
                    lead['website'] = ""  # Mark as unreachable
            
            lead['status'] = 'enriched'
            lead['enriched_at'] = datetime.now().isoformat()
            self.enriched_count += 1
            
        except Exception as e:
            lead['error'] = str(e)
            self.failed_count += 1
        
        return lead
    
    def merge_lead_sources(self, bootstrap_leads: list, existing_leads: list) -> list:
        """Merge bootstrap and existing leads, deduplicating by company name + city."""
        merged = {}
        
        # Add existing leads first (they have priority)
        for lead in existing_leads:
            key = f"{lead.get('company_name', '').lower()}_{lead.get('city', '').lower()}"
            merged[key] = lead
        
        # Add bootstrap leads if not already present
        for lead in bootstrap_leads:
            key = f"{lead.get('company_name', '').lower()}_{lead.get('city', '').lower()}"
            if key not in merged:
                merged[key] = lead
        
        return list(merged.values())
    
    def run(self, input_bootstrap: str = None, input_existing: str = None, output_file: str = None):
        """Run enrichment pipeline."""
        
        # Defaults
        if not input_bootstrap:
            input_bootstrap = "/home/molt/devspace/testhelp24-leads/data/bootstrap_leads.json"
        if not input_existing:
            input_existing = "/home/molt/devspace/testhelp24-leads/data/final_leads.json"
        if not output_file:
            output_file = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"
        
        print("=" * 70)
        print("🔧 Lead Enrichment Pipeline")
        print("=" * 70)
        print()
        
        # Load bootstrap leads
        print(f"📥 Loading bootstrap leads from {os.path.basename(input_bootstrap)}...")
        bootstrap_leads = []
        if os.path.exists(input_bootstrap):
            with open(input_bootstrap, 'r', encoding='utf-8') as f:
                bootstrap_leads = json.load(f)
            print(f"   ✓ Loaded {len(bootstrap_leads)} leads")
        else:
            print(f"   ⚠️ File not found")
        
        # Load existing leads
        print(f"📥 Loading existing leads from {os.path.basename(input_existing)}...")
        existing_leads = []
        if os.path.exists(input_existing):
            with open(input_existing, 'r', encoding='utf-8') as f:
                existing_leads = json.load(f)
            print(f"   ✓ Loaded {len(existing_leads)} leads")
        else:
            print(f"   ⚠️ File not found")
        
        print()
        
        # Merge leads
        print("🔀 Merging lead sources (deduplicating)...")
        merged_leads = self.merge_lead_sources(bootstrap_leads, existing_leads)
        print(f"   ✓ Merged into {len(merged_leads)} unique leads")
        print()
        
        # Enrich leads
        print("⚡ Enriching leads (finding emails, validating websites)...")
        print("   (This may take a few minutes...)")
        enriched = []
        for i, lead in enumerate(merged_leads, 1):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(merged_leads)}")
            
            enriched_lead = self.enrich_lead(lead)
            enriched.append(enriched_lead)
            time.sleep(0.5)  # Rate limiting
        
        print(f"   ✓ Enriched: {self.enriched_count}")
        print(f"   ✗ Failed: {self.failed_count}")
        print()
        
        # Save enriched leads
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved enriched leads to {output_file}")
        print()
        
        # Statistics
        print("=" * 70)
        print("📊 Statistics")
        print("=" * 70)
        with_email = len([l for l in enriched if l.get('email')])
        with_website = len([l for l in enriched if l.get('website')])
        print(f"Total leads: {len(enriched)}")
        print(f"With email: {with_email} ({with_email/len(enriched)*100:.1f}%)")
        print(f"With valid website: {with_website} ({with_website/len(enriched)*100:.1f}%)")
        print()

def main():
    enricher = LeadEnricher()
    enricher.run()

if __name__ == "__main__":
    main()
