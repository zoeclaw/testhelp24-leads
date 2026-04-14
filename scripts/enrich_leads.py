#!/usr/bin/env python3
"""
Lead enrichment script - adds contact details, validates websites, finds emails.
Volume-first behavior keeps weak-but-useful leads and preserves discovered websites
instead of discarding them when a quick validation probe fails.
"""

import os
import json
import time
import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests

from schema import merge_unique_strings
from utils import deduplicate_companies, merge_company_records, normalize_company


class LeadEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.enriched_count = 0
        self.failed_count = 0

    def _extract_relevant_emails(self, text: str) -> List[str]:
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, text or "")
        relevant_keywords = [
            'info', 'kontakt', 'hello', 'sales', 'recruitment',
            'hr', 'jobs', 'careers', 'contact', 'service', 'team'
        ]

        ranked = []
        for email in set(found_emails):
            local_part = email.split('@')[0].lower()
            priority = 1 if any(keyword in local_part for keyword in relevant_keywords) else 0
            ranked.append((priority, email))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [email for _, email in ranked[:3]]

    def find_emails_from_website(self, website: str) -> list:
        """Scrape website and common contact pages for email addresses."""
        if not website or not website.startswith('http'):
            return []

        candidate_urls = [
            website,
            urljoin(website if website.endswith('/') else website + '/', 'kontakt'),
            urljoin(website if website.endswith('/') else website + '/', 'contact'),
            urljoin(website if website.endswith('/') else website + '/', 'impressum'),
            urljoin(website if website.endswith('/') else website + '/', 'imprint'),
        ]

        emails = []
        seen_pages = set()

        for candidate_url in candidate_urls:
            if candidate_url in seen_pages:
                continue
            seen_pages.add(candidate_url)

            try:
                response = self.session.get(candidate_url, timeout=6)
                response.raise_for_status()
                response.encoding = 'utf-8'
                emails.extend(self._extract_relevant_emails(response.text))
            except requests.exceptions.RequestException:
                continue

        unique = []
        for email in emails:
            if email not in unique:
                unique.append(email)
        return unique[:3]

    def validate_website(self, website: str) -> bool:
        """Check if website is accessible, with GET fallback for HEAD-blocking sites."""
        if not website or not website.startswith('http'):
            return False

        try:
            response = self.session.head(website, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                return True
            if response.status_code in {403, 405}:
                response = self.session.get(website, timeout=6, allow_redirects=True)
                return response.status_code < 400
            return False
        except requests.exceptions.RequestException:
            try:
                response = self.session.get(website, timeout=6, allow_redirects=True)
                return response.status_code < 400
            except requests.exceptions.RequestException:
                return False

    def enrich_lead(self, lead: dict) -> dict:
        """Enrich a single lead with additional data."""
        lead = normalize_company(lead)

        try:
            website = lead.get('website', '')
            if website and not website.startswith('http'):
                website = f"https://{website}"
                lead['website'] = website

            if website:
                website_is_reachable = self.validate_website(website)
                lead['website_status'] = 'reachable' if website_is_reachable else 'unverified'

                emails = self.find_emails_from_website(website)
                if emails:
                    if not lead.get('email'):
                        lead['email'] = emails[0]
                    if len(emails) > 1:
                        existing_additional = lead.get('additional_emails', []) or []
                        lead['additional_emails'] = merge_unique_strings(existing_additional + emails[1:])[:5]

            lead['lead_stage'] = 'contact_enriched'
            lead['status'] = 'enriched'
            lead['enriched_at'] = datetime.now().isoformat()
            self.enriched_count += 1

        except Exception as e:
            lead['error'] = str(e)
            self.failed_count += 1

        return lead

    def merge_lead_sources(self, bootstrap_leads: list, existing_leads: list) -> list:
        """Merge bootstrap and existing leads, preferring the richest combined record."""
        combined = [normalize_company(lead) for lead in existing_leads + bootstrap_leads]
        deduplicated = deduplicate_companies(combined)

        # Ensure explicit merge pass if the same record appears multiple times with complementary fields.
        merged_by_key = {}
        for lead in deduplicated:
            key = f"{lead.get('company_name', '').lower()}::{lead.get('city', '').lower()}::{lead.get('website', '').lower()}"
            if key in merged_by_key:
                merged_by_key[key] = merge_company_records(merged_by_key[key], lead)
            else:
                merged_by_key[key] = lead

        return list(merged_by_key.values())

    def run(self, input_bootstrap: str = None, input_existing: str = None, output_file: str = None):
        """Run enrichment pipeline."""

        if not input_bootstrap:
            input_bootstrap = "/home/molt/devspace/testhelp24-leads/data/bootstrap_leads.json"
        if not input_existing:
            input_existing = "/home/molt/devspace/testhelp24-leads/data/final_leads.json"
        if not output_file:
            output_file = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"

        print("=" * 70)
        print("🔧 Lead Enrichment Pipeline (volume-first)")
        print("=" * 70)
        print()

        print(f"📥 Loading bootstrap leads from {os.path.basename(input_bootstrap)}...")
        bootstrap_leads = []
        if os.path.exists(input_bootstrap):
            with open(input_bootstrap, 'r', encoding='utf-8') as f:
                bootstrap_leads = json.load(f)
            print(f"   ✓ Loaded {len(bootstrap_leads)} leads")
        else:
            print(f"   ⚠️ File not found")

        print(f"📥 Loading existing leads from {os.path.basename(input_existing)}...")
        existing_leads = []
        if os.path.exists(input_existing):
            with open(input_existing, 'r', encoding='utf-8') as f:
                existing_leads = json.load(f)
            print(f"   ✓ Loaded {len(existing_leads)} leads")
        else:
            print(f"   ⚠️ File not found")

        print()
        print("🔀 Merging lead sources (favoring richer merged records)...")
        merged_leads = self.merge_lead_sources(bootstrap_leads, existing_leads)
        print(f"   ✓ Merged into {len(merged_leads)} unique leads")
        print()

        print("⚡ Enriching leads (finding emails, validating websites)...")
        print("   (Volume-first: keep leads even when websites cannot be confirmed immediately)")
        enriched = []
        for i, lead in enumerate(merged_leads, 1):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(merged_leads)}")

            enriched_lead = self.enrich_lead(lead)
            enriched.append(enriched_lead)
            time.sleep(0.25)

        print(f"   ✓ Enriched: {self.enriched_count}")
        print(f"   ✗ Failed: {self.failed_count}")
        print()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved enriched leads to {output_file}")
        print()

        print("=" * 70)
        print("📊 Statistics")
        print("=" * 70)
        with_email = len([l for l in enriched if l.get('email')])
        with_phone = len([l for l in enriched if l.get('phone')])
        with_website = len([l for l in enriched if l.get('website')])
        with_reachable_website = len([l for l in enriched if l.get('website_status') == 'reachable'])
        print(f"Total leads: {len(enriched)}")
        if enriched:
            print(f"With email: {with_email} ({with_email/len(enriched)*100:.1f}%)")
            print(f"With phone: {with_phone} ({with_phone/len(enriched)*100:.1f}%)")
            print(f"With website: {with_website} ({with_website/len(enriched)*100:.1f}%)")
            print(f"Website reachable now: {with_reachable_website} ({with_reachable_website/len(enriched)*100:.1f}%)")
        print()


def main():
    enricher = LeadEnricher()
    enricher.run()


if __name__ == "__main__":
    main()
