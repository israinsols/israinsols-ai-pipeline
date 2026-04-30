"""
Run the Freelancer pipeline end-to-end:
1. Scrape Freelancer.com projects
2. Save new leads to the database
3. Send Telegram alerts for unnotified Freelancer leads

Usage:
    python run_freelancer_pipeline.py
"""
import asyncio
import os
import django
import time
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.scraper.freelancer import FreelancerScraper
from leads.tasks import _save_new_leads, _send_single_alert_sync
from leads.models import ScrapedLead

QUERIES = [
    "python django web development",
    "react developer frontend",
    "web scraping automation python",
    "shopify store setup",
    "mobile app development",
    "website design",
]


def main():
    print("=" * 65)
    print("Freelancer Pipeline — Scrape, Save, Alert")
    print("=" * 65)

    all_leads = []
    for query in QUERIES:
        print(f"\n🔍 Scraping: '{query}'")
        scraper = FreelancerScraper(search_query=query, max_results=50, max_pages=2)
        projects = asyncio.run(scraper.scrape())
        print(f"   Found {len(projects)} projects")
        all_leads.extend(projects)

    if not all_leads:
        print("\nNo freelancer leads found. Exiting.")
        return

    print(f"\n💾 Saving {len(all_leads)} leads to database...")
    result = _save_new_leads(all_leads)
    print(f"   Total scraped:  {result['total']}")
    print(f"   New saved:    {result['saved']}")
    print(f"   Duplicates:   {result['duplicates']}")
    print(f"   Alerts sent:  {result['saved']} (immediate)")

    print(f"\n--- RESULT ---")
    print(f"Total scraped : {result['total']}")
    print(f"Newly saved   : {result['saved']}")
    print(f"Duplicates    : {result['duplicates']}")
    print(f"Alerts sent   : {result['saved']} (immediate)")

    # Show DB state (sync)
    print(f"\n--- DATABASE STATE ---")
    total = ScrapedLead.objects.count()
    by_source = ScrapedLead.objects.values('source').annotate(c=Count('id')).order_by('-c')
    print(f"Total leads: {total}")
    for s in by_source:
        print(f"  {s['source']:15s}: {s['c']}")

    # Show 5 sample Freelancer leads
    print(f"\n--- SAMPLE FREELANCER PROJECTS (latest 5) ---")
    samples = ScrapedLead.objects.filter(source='freelancer').order_by('-scraped_at')[:5]
    for i, lead in enumerate(samples, 1):
        print(f"\n[{i}] {lead.title[:65]}")
        print(f"     Budget  : {lead.budget or 'N/A'}")
        print(f"     Country : {lead.client_country or 'N/A'}")
        print(f"     Skills  : {lead.tech_stack}")
        print(f"     URL     : {lead.url[:75]}")


if __name__ == '__main__':
    main()
