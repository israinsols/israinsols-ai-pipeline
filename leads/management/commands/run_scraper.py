"""
Django Management Command: run_scraper

Usage:
    python manage.py run_scraper --query "react developer"
"""
import os
import sys
import io
import logging
import asyncio
from django.core.management.base import BaseCommand

# ============================================================
# FORCE UTF-8 FOR CONSOLE AND LOGGING
# ============================================================
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.INFO)

os.environ['PYTHONUTF8'] = '1'
# ============================================================


class Command(BaseCommand):
    help = 'Run the Freelancer.com lead scraper manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            default='python django web development',
            help='Search query for Freelancer.com',
        )
        parser.add_argument(
            '--results',
            type=int,
            default=50,
            help='Max results to fetch',
        )
        parser.add_argument(
            '--visible',
            action='store_true',
            help='Run browser in visible mode',
        )

    def handle(self, *args, **options):
        headless = not options['visible']

        self.stdout.write(self.style.WARNING(
            f"\n🤖 Starting Freelancer.com scraper for: {options['query']}...\n"
        ))

        from leads.scraper.freelancer import FreelancerScraper
        scraper = FreelancerScraper(
            search_query=options['query'],
            max_results=options['results'],
            headless=headless,
        )

        # Run scraper (async)
        leads_data = asyncio.run(scraper.scrape())

        self.stdout.write(f"\n📋 Found {len(leads_data)} leads\n")

        # Save to database
        from leads.tasks import _save_new_leads
        result = _save_new_leads(leads_data)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Results:\n"
            f"   Total found:  {result['total']}\n"
            f"   New saved:    {result['saved']}\n"
            f"   Duplicates:   {result['duplicates']}\n"
        ))

        # Show saved leads
        if result['saved'] > 0:
            from leads.models import ScrapedLead
            recent = ScrapedLead.objects.filter(
                status=ScrapedLead.Status.UNNOTIFIED
            ).order_by('-scraped_at')[:result['saved']]

            self.stdout.write("\n📋 Newly saved leads:")
            for lead in recent:
                self.stdout.write(
                    f"  • {lead.title[:60]}"
                    f" | {lead.budget or 'No budget'}"
                    f" | {lead.tech_stack_display or 'No tech'}"
                )