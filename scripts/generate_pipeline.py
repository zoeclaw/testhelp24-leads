#!/usr/bin/env python3
"""
Lead Pipeline Generator - creates prioritized, action-ready lead lists.
Volume-first edition: prioritize breadth and contactable volume over perfect enrichment.
"""

import json
import os
from datetime import datetime
from typing import Dict, List


class LeadScorer:
    """Score leads for partnership potential under a volume-first strategy."""

    def __init__(self):
        self.weights = {
            'has_email': 25,
            'has_phone': 25,
            'has_website': 15,
            'has_location': 10,
            'company_size': 10,
            'enrichment_status': 5,
            'source_confidence': 5,
            'decision_maker': 10,
        }

    def score_lead(self, lead: dict) -> float:
        """Calculate lead quality score (0-100)."""
        score = 0

        if lead.get('email') or lead.get('additional_emails'):
            score += self.weights['has_email']

        if lead.get('phone'):
            score += self.weights['has_phone']

        if lead.get('website'):
            score += self.weights['has_website']

        if lead.get('city') or lead.get('location') or lead.get('address'):
            score += self.weights['has_location']

        company_size = str(lead.get('company_size', '')).lower()
        if any(token in company_size for token in ['1000', '500']):
            score += self.weights['company_size']
        elif any(token in company_size for token in ['100', '300', '200']):
            score += self.weights['company_size'] * 0.6

        if lead.get('status') == 'enriched' and lead.get('enriched_at'):
            score += self.weights['enrichment_status']

        if lead.get('source') and lead.get('source') != 'unknown':
            score += self.weights['source_confidence']

        if lead.get('contact_person') or lead.get('decision_makers'):
            score += self.weights['decision_maker']

        return min(score, 100)

    def categorize_by_tier(self, leads: List[dict]) -> Dict[str, List[dict]]:
        """Categorize leads into tiers for a volume-first outreach strategy."""
        tiers = {
            'tier_1_ready': [],      # Any direct contact path exists now
            'tier_2_partial': [],    # Known company with locality, needs contact enrichment
            'tier_3_todo': []        # Weak records needing more discovery
        }

        for lead in leads:
            has_email = bool(lead.get('email') or lead.get('additional_emails'))
            has_website = bool(lead.get('website'))
            has_phone = bool(lead.get('phone'))
            has_locality = bool(lead.get('city') or lead.get('location') or lead.get('address'))

            has_decision_maker = bool(lead.get('contact_person') or lead.get('decision_makers'))

            if has_email or has_phone or has_website:
                if has_decision_maker:
                    lead['outreach_priority'] = 'tier_1_named_contact'
                else:
                    lead['outreach_priority'] = 'tier_1_general_contact'
                tiers['tier_1_ready'].append(lead)
            elif has_locality:
                lead['outreach_priority'] = 'tier_2_partial'
                tiers['tier_2_partial'].append(lead)
            else:
                lead['outreach_priority'] = 'tier_3_todo'
                tiers['tier_3_todo'].append(lead)

        return tiers


def main():
    print("=" * 70)
    print("🎯 Lead Pipeline Generator (volume-first)")
    print("=" * 70)
    print()

    enriched_file = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"

    print(f"📥 Loading enriched leads...")
    with open(enriched_file, 'r', encoding='utf-8') as f:
        enriched_leads = json.load(f)
    print(f"   ✓ Loaded {len(enriched_leads)} leads")
    print()

    print("📊 Scoring leads...")
    scorer = LeadScorer()
    for lead in enriched_leads:
        lead['quality_score'] = scorer.score_lead(lead)

    enriched_leads.sort(key=lambda x: x['quality_score'], reverse=True)
    print("   ✓ Scored all leads")
    print()

    print("📈 Categorizing by tier...")
    tiers = scorer.categorize_by_tier(enriched_leads)

    for tier_name, leads in tiers.items():
        print(f"   {tier_name}: {len(leads)} leads")
    print()

    output_dir = "/home/molt/devspace/testhelp24-leads/data/pipeline"
    os.makedirs(output_dir, exist_ok=True)

    all_scored_file = f"{output_dir}/all_leads_scored.json"
    with open(all_scored_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_leads, f, ensure_ascii=False, indent=2)
    print(f"✓ All leads: {all_scored_file}")

    for tier_name, leads in tiers.items():
        tier_file = f"{output_dir}/{tier_name}.json"
        with open(tier_file, 'w', encoding='utf-8') as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        print(f"✓ {tier_name}: {tier_file}")

    print()
    print("=" * 70)
    print("📋 Action Plan")
    print("=" * 70)
    print()

    action_plan = {
        "generated_at": datetime.now().isoformat(),
        "strategy": "volume_first",
        "total_leads": len(enriched_leads),
        "by_tier": {
            "tier_1_ready": {
                "count": len(tiers['tier_1_ready']),
                "named_contact_count": len([lead for lead in tiers['tier_1_ready'] if lead.get('contact_person') or lead.get('decision_makers')]),
                "action": "Start outreach immediately using any available channel",
                "channels": ["Email", "Phone", "Website contact form"],
                "priority": "HIGH"
            },
            "tier_2_partial": {
                "count": len(tiers['tier_2_partial']),
                "action": "Batch enrich missing contact channels while keeping these in the active pipeline",
                "channels": ["Website lookup", "Google search", "Maps lookup", "LinkedIn"],
                "priority": "MEDIUM"
            },
            "tier_3_todo": {
                "count": len(tiers['tier_3_todo']),
                "action": "Use only for broadening coverage when higher tiers are exhausted",
                "channels": ["Manual research", "Directory search", "Maps lookup"],
                "priority": "LOW"
            }
        },
        "outreach_strategy": {
            "week_1": f"Contact Tier 1 immediately ({len(tiers['tier_1_ready'])} leads) across all available channels",
            "week_2": f"Upgrade Tier 2 in batches while continuing outreach ({len(tiers['tier_2_partial'])} leads)",
            "ongoing": f"Expand coverage and recycle Tier 3 into Tier 2 ({len(tiers['tier_3_todo'])} leads)",
            "cadence": "10-20 outreach attempts per day, spread across channels"
        },
        "success_metrics": {
            "target_volume": f"{len(tiers['tier_1_ready']) + len(tiers['tier_2_partial'])} active leads in the top-of-funnel",
            "target_conversion": "3-8% initial response rate",
            "partnership_rate": "15-25% of qualified respondents",
            "monthly_revenue_potential": f"€{len(tiers['tier_1_ready']) * 50}/month (conservative starting point)"
        }
    }

    plan_file = f"{output_dir}/action_plan.json"
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(action_plan, f, ensure_ascii=False, indent=2)
    print(f"✓ Action plan: {plan_file}")
    print()

    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"Total leads: {len(enriched_leads)}")
    print(f"  🚀 Tier 1 (any contact channel): {len(tiers['tier_1_ready'])} - OUTREACH NOW")
    print(f"  🧩 Tier 2 (known but missing contact path): {len(tiers['tier_2_partial'])} - Batch enrich")
    print(f"  🔍 Tier 3 (minimal signal): {len(tiers['tier_3_todo'])} - Coverage backlog")
    print()

    average_score = sum(l['quality_score'] for l in enriched_leads) / len(enriched_leads) if enriched_leads else 0
    print(f"Average quality score: {average_score:.1f}/100")
    print()

    print("🏆 Top 10 Leads (by quality score)")
    print("-" * 70)
    for i, lead in enumerate(enriched_leads[:10], 1):
        print(f"{i:2}. {lead['company_name']:<30} | {lead.get('city', lead.get('location', 'N/A')):<12} | Score: {lead['quality_score']:5.1f}")
        if lead.get('email'):
            print(f"    📧 {lead['email']}")
        elif lead.get('additional_emails'):
            print(f"    📧 {lead['additional_emails'][0]}")
        if lead.get('phone'):
            print(f"    📞 {lead['phone']}")
        if lead.get('website'):
            print(f"    🌐 {lead['website']}")
        print()

    print("=" * 70)
    print("✅ Volume-first pipeline ready for outreach!")
    print("=" * 70)


if __name__ == "__main__":
    main()
