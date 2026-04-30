"""
End-to-end test: Freelancer.com → Database → Show results
Sync version — no async ORM issues.
Usage: python test_freelancer_e2e.py
"""
import asyncio, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.scraper.freelancer import FreelancerScraper
from leads.tasks import _save_new_leads
from leads.models import ScrapedLead
from django.db.models import Count

QUERIES = [
    "python django web development",
    "react developer frontend",
    "web scraping automation python",
    "django rest api backend",
]

def main():
    print("=" * 65)
    print("Freelancer.com → DB End-to-End Test")
    print("=" * 65)

    all_leads = []

    # Step 1: Scrape all queries (async → sync via asyncio.run)
    for query in QUERIES:
        print(f"\n🔍 Scraping: '{query}'")
        scraper = FreelancerScraper(search_query=query, max_results=50)
        leads = asyncio.run(scraper.scrape())
        print(f"   Found: {len(leads)} projects")
        all_leads.extend(leads)

    # Step 2: Transform leads (sync — no ORM)
    print(f"\nTransforming {len(all_leads)} leads...")
    s = FreelancerScraper()
    transformed = [s.transform_lead(l) for l in all_leads]

    # Step 3: Save to DB (sync — Django ORM)
    print(f"💾 Saving to database...")
    result = _save_new_leads(transformed)

    print(f"\n--- RESULT ---")
    print(f"Total scraped : {result['total']}")
    print(f"Newly saved   : {result['saved']}")
    print(f"Duplicates    : {result['duplicates']}")

    # Step 4: Show DB state (sync)
    print(f"\n--- DATABASE STATE ---")
    total = ScrapedLead.objects.count()
    by_source = ScrapedLead.objects.values('source').annotate(c=Count('id')).order_by('-c')
    print(f"Total leads: {total}")
    for s in by_source:
        print(f"  {s['source']:15s}: {s['c']}")

    # Step 5: Show 5 sample Freelancer leads
    print(f"\n--- SAMPLE FREELANCER PROJECTS (latest 5) ---")
    samples = ScrapedLead.objects.filter(source='freelancer').order_by('-scraped_at')[:5]
    for i, lead in enumerate(samples, 1):
        print(f"\n[{i}] {lead.title[:65]}")
        print(f"     Budget  : {lead.budget or 'N/A'}")
        print(f"     Country : {lead.client_country or 'N/A'}")
        print(f"     Skills  : {lead.tech_stack}")
        print(f"     URL     : {lead.url[:75]}")


if __name__ == "__main__":
    main()
