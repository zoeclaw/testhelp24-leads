#!/usr/bin/env python3
"""
Lead Pipeline Generator - creates prioritized, action-ready lead lists.
Scores leads by quality, enrichment status, and partnership fit.
"""

import json
import os
from datetime import datetime
from typing import List, Dict

class LeadScorer:
    """Score leads for partnership potential."""
    
    def __init__(self):
        self.weights = {
            'has_email': 30,
            'has_phone': 25,
            'has_website': 20,
            'company_size': 15,
            'enrichment_status': 10
        }
    
    def score_lead(self, lead: dict) -> float:
        """Calculate lead quality score (0-100)."""
        score = 0
        
        # Email (most valuable for outreach)
        if lead.get('email') or lead.get('additional_emails'):
            score += self.weights['has_email']
        
        # Phone
        if lead.get('phone'):
            score += self.weights['has_phone']
        
        # Website
        if lead.get('website'):
            score += self.weights['has_website']
        
        # Company size (500+ employees = higher staffing volume)
        company_size = lead.get('company_size', '').lower()
        if '1000' in company_size or '500' in company_size:
            score += self.weights['company_size']
        elif '100' in company_size or '300' in company_size:
            score += self.weights['company_size'] * 0.5
        
        # Enrichment status
        if lead.get('status') == 'enriched' and lead.get('enriched_at'):
            score += self.weights['enrichment_status']
        
        return min(score, 100)  # Cap at 100
    
    def categorize_by_tier(self, leads: List[dict]) -> Dict[str, List[dict]]:
        """Categorize leads into tiers for outreach strategy."""
        tiers = {
            'tier_1_ready': [],      # Email + website (ready to contact)
            'tier_2_partial': [],     # Website or phone only
            'tier_3_todo': []         # Needs enrichment
        }
        
        for lead in leads:
            has_email = bool(lead.get('email') or lead.get('additional_emails'))
            has_website = bool(lead.get('website'))
            has_phone = bool(lead.get('phone'))
            
            if has_email and has_website:
                tiers['tier_1_ready'].append(lead)
            elif has_website or has_phone:
                tiers['tier_2_partial'].append(lead)
            else:
                tiers['tier_3_todo'].append(lead)
        
        return tiers

def main():
    print("=" * 70)
    print("🎯 Lead Pipeline Generator")
    print("=" * 70)
    print()
    
    # Load enriched leads
    enriched_file = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"
    
    print(f"📥 Loading enriched leads...")
    with open(enriched_file, 'r', encoding='utf-8') as f:
        enriched_leads = json.load(f)
    print(f"   ✓ Loaded {len(enriched_leads)} leads")
    print()
    
    # Score leads
    print("📊 Scoring leads...")
    scorer = LeadScorer()
    for lead in enriched_leads:
        lead['quality_score'] = scorer.score_lead(lead)
    
    # Sort by score
    enriched_leads.sort(key=lambda x: x['quality_score'], reverse=True)
    print(f"   ✓ Scored all leads")
    print()
    
    # Categorize by tier
    print("📈 Categorizing by tier...")
    tiers = scorer.categorize_by_tier(enriched_leads)
    
    for tier_name, leads in tiers.items():
        print(f"   {tier_name}: {len(leads)} leads")
    print()
    
    # Save pipeline
    output_dir = "/home/molt/devspace/testhelp24-leads/data/pipeline"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save all scored leads
    all_scored_file = f"{output_dir}/all_leads_scored.json"
    with open(all_scored_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_leads, f, ensure_ascii=False, indent=2)
    print(f"✓ All leads: {all_scored_file}")
    
    # Save by tier
    for tier_name, leads in tiers.items():
        tier_file = f"{output_dir}/{tier_name}.json"
        with open(tier_file, 'w', encoding='utf-8') as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        print(f"✓ {tier_name}: {tier_file}")
    
    print()
    
    # Generate action plan
    print("=" * 70)
    print("📋 Action Plan")
    print("=" * 70)
    print()
    
    action_plan = {
        "generated_at": datetime.now().isoformat(),
        "total_leads": len(enriched_leads),
        "by_tier": {
            "tier_1_ready": {
                "count": len(tiers['tier_1_ready']),
                "action": "Ready for immediate outreach",
                "channels": ["Email", "Website contact form"],
                "priority": "HIGH"
            },
            "tier_2_partial": {
                "count": len(tiers['tier_2_partial']),
                "action": "Requires partial enrichment (find missing email/phone)",
                "channels": ["Phone", "Website scraping", "LinkedIn"],
                "priority": "MEDIUM"
            },
            "tier_3_todo": {
                "count": len(tiers['tier_3_todo']),
                "action": "Needs full enrichment before outreach",
                "channels": ["Manual research", "Google search", "Maps lookup"],
                "priority": "LOW"
            }
        },
        "outreach_strategy": {
            "week_1": f"Contact Tier 1 ({len(tiers['tier_1_ready'])} leads) - high conversion",
            "week_2": f"Enrich & contact Tier 2 ({len(tiers['tier_2_partial'])} leads)",
            "ongoing": f"Continuously enrich Tier 3 ({len(tiers['tier_3_todo'])} leads)",
            "cadence": "3-5 outreaches per day to avoid spam filters"
        },
        "success_metrics": {
            "target_conversion": "5-10% initial response rate",
            "partnership_rate": "20-30% of respondents",
            "monthly_revenue_potential": f"€{len(tiers['tier_1_ready']) * 50}/month (conservative)"
        }
    }
    
    plan_file = f"{output_dir}/action_plan.json"
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(action_plan, f, ensure_ascii=False, indent=2)
    print(f"✓ Action plan: {plan_file}")
    print()
    
    # Print summary
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"Total leads: {len(enriched_leads)}")
    print(f"  📧 Tier 1 (Email + Website): {len(tiers['tier_1_ready'])} - READY NOW")
    print(f"  📱 Tier 2 (Partial data): {len(tiers['tier_2_partial'])} - Need enrichment")
    print(f"  🔍 Tier 3 (Minimal data): {len(tiers['tier_3_todo'])} - Needs research")
    print()
    print(f"Average quality score: {sum(l['quality_score'] for l in enriched_leads) / len(enriched_leads):.1f}/100")
    print()
    
    # Top 10 quality leads
    print("🏆 Top 10 Leads (by quality score)")
    print("-" * 70)
    for i, lead in enumerate(enriched_leads[:10], 1):
        print(f"{i:2}. {lead['company_name']:<30} | {lead.get('city', 'N/A'):<12} | Score: {lead['quality_score']:5.1f}")
        if lead.get('email'):
            print(f"    📧 {lead['email']}")
        elif lead.get('additional_emails'):
            print(f"    📧 {lead['additional_emails'][0]}")
        if lead.get('phone'):
            print(f"    📞 {lead['phone']}")
        print()
    
    print("=" * 70)
    print("✅ Pipeline ready for outreach!")
    print("=" * 70)

if __name__ == "__main__":
    main()
