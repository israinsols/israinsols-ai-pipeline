"""
Test Freelancer.com API scraper — real client project listings.
Usage: python test_freelancer.py
"""
import asyncio, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.scraper.freelancer import FreelancerScraper

QUERIES = [
    "python django",
    "react developer",
    "web scraping",
]

async def main():
    print("=" * 65)
    print("Freelancer.com API Test — Real Client Project Postings")
    print("=" * 65)

    for query in QUERIES:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 50)

        scraper = FreelancerScraper(search_query=query, max_results=10)
        leads = await scraper.scrape()

        print(f"Found {len(leads)} client projects\n")
        for i, lead in enumerate(leads[:5], 1):
            skills = lead.get('tech_stack', [])
            skills_str = ', '.join(skills[:5]) if isinstance(skills, list) else skills
            country = lead.get('client_country') or 'Unknown'
            print(f"  [{i}] {lead['title'][:65]}")
            print(f"       Budget  : {lead.get('budget') or 'Not specified'}")
            print(f"       Country : {country}")
            print(f"       Skills  : {skills_str or 'Not specified'}")
            print(f"       URL     : {lead['url'][:70]}")
            print(f"       Desc    : {lead.get('description', '')[:120]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())
