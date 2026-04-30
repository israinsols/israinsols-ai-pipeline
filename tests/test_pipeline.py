"""
Israinsols Pipeline - Tests

Test the core components:
1. ScrapedLead model (creation, dedup, status transitions)
2. Scraper (DemoScraper output format)
3. Bot formatters (message formatting)
"""
import asyncio
import hashlib
from django.test import TestCase
from django.utils import timezone
from leads.models import ScrapedLead, ScrapeLog


class ScrapedLeadModelTests(TestCase):
    """Phase 2: Test database model and deduplication"""

    def test_create_lead(self):
        """Test basic lead creation"""
        lead = ScrapedLead.objects.create(
            title="React Developer Needed",
            description="Build a dashboard",
            budget="$500 - $1,000",
            tech_stack=["React", "Node.js"],
            url="https://example.com/job/12345",
            source="upwork",
        )

        self.assertEqual(lead.title, "React Developer Needed")
        self.assertEqual(lead.status, ScrapedLead.Status.UNNOTIFIED)
        self.assertIsNotNone(lead.content_hash)
        self.assertIsNotNone(lead.scraped_at)

    def test_content_hash_auto_generated(self):
        """Test that content_hash is automatically generated on save"""
        lead = ScrapedLead(
            title="Test Job",
            url="https://example.com/job/99999",
        )
        lead.save()

        expected_hash = hashlib.sha256(
            "test job|https://example.com/job/99999".encode()
        ).hexdigest()

        self.assertEqual(lead.content_hash, expected_hash)

    def test_duplicate_url_rejected(self):
        """Test that duplicate URLs are rejected"""
        ScrapedLead.objects.create(
            title="Job 1",
            url="https://example.com/job/same-url",
        )

        with self.assertRaises(Exception):
            ScrapedLead.objects.create(
                title="Job 2",
                url="https://example.com/job/same-url",
            )

    def test_status_transitions(self):
        """Test status update methods"""
        lead = ScrapedLead.objects.create(
            title="Test Lead",
            url="https://example.com/job/status-test",
        )

        # Initial status
        self.assertEqual(lead.status, ScrapedLead.Status.UNNOTIFIED)

        # Mark as notified
        lead.mark_as_notified()
        lead.refresh_from_db()
        self.assertEqual(lead.status, ScrapedLead.Status.NOTIFIED)
        self.assertIsNotNone(lead.notified_at)

        # Mark as contacted
        lead.mark_as_contacted()
        lead.refresh_from_db()
        self.assertEqual(lead.status, ScrapedLead.Status.CONTACTED)

        # Mark as rejected
        lead.mark_as_rejected()
        lead.refresh_from_db()
        self.assertEqual(lead.status, ScrapedLead.Status.REJECTED)

    def test_tech_stack_display(self):
        """Test tech_stack_display property"""
        lead = ScrapedLead(
            title="Test",
            url="https://example.com/1",
            tech_stack=["React", "Django", "PostgreSQL"],
        )
        self.assertEqual(lead.tech_stack_display, "React, Django, PostgreSQL")

    def test_is_high_value(self):
        """Test is_high_value property"""
        # High value
        lead = ScrapedLead(title="Test", url="https://ex.com/1", budget="$1,000 - $5,000")
        self.assertTrue(lead.is_high_value)

        # Low value
        lead2 = ScrapedLead(title="Test", url="https://ex.com/2", budget="$100")
        self.assertFalse(lead2.is_high_value)

        # No budget
        lead3 = ScrapedLead(title="Test", url="https://ex.com/3", budget="")
        self.assertFalse(lead3.is_high_value)

    def test_ordering(self):
        """Test that leads are ordered by scraped_at desc"""
        lead1 = ScrapedLead.objects.create(
            title="First", url="https://example.com/first"
        )
        lead2 = ScrapedLead.objects.create(
            title="Second", url="https://example.com/second"
        )

        leads = list(ScrapedLead.objects.all())
        self.assertEqual(leads[0].title, "Second")  # Most recent first


class ScrapeLogTests(TestCase):
    """Test scrape logging"""

    def test_create_log(self):
        """Test scrape log creation"""
        log = ScrapeLog.objects.create(
            source='demo',
            run_status=ScrapeLog.RunStatus.SUCCESS,
            total_found=10,
            new_saved=5,
            duplicates_skipped=5,
            duration_seconds=12.5,
        )

        self.assertEqual(log.source, 'demo')
        self.assertEqual(log.total_found, 10)
        self.assertEqual(log.new_saved, 5)


class FormatterTests(TestCase):
    """Phase 4: Test message formatting"""

    def test_format_lead_message(self):
        """Test lead message formatting"""
        from leads.bot.formatters import format_lead_message

        lead = ScrapedLead.objects.create(
            title="React Developer Needed",
            budget="$500 - $1,000",
            tech_stack=["React", "Node.js"],
            url="https://example.com/job/123",
            source="upwork",
            client_country="United States",
        )

        message = format_lead_message(lead)

        self.assertIn("React Developer Needed", message)
        self.assertIn("$500", message)
        self.assertIn("React", message)
        self.assertIn("United States", message)
        self.assertIn("New Lead Found", message)

    def test_format_stats_message(self):
        """Test stats message formatting"""
        from leads.bot.formatters import format_stats_message

        stats = {
            'total': 100,
            'unnotified': 10,
            'notified': 40,
            'contacted': 30,
            'applied': 15,
            'rejected': 5,
            'today': 8,
            'this_week': 45,
            'high_value': 20,
        }

        message = format_stats_message(stats)
        self.assertIn("100", message)
        self.assertIn("Pipeline Stats", message)


class KeyboardTests(TestCase):
    """Phase 4: Test keyboard generation"""

    def test_lead_keyboard(self):
        """Test inline keyboard generation"""
        from leads.bot.keyboards import get_lead_keyboard

        keyboard = get_lead_keyboard(42, "https://example.com/job/42")
        data = keyboard.to_dict()

        # Should have 3 rows
        self.assertEqual(len(data['inline_keyboard']), 3)

        # First row: Apply Now (URL button)
        self.assertEqual(data['inline_keyboard'][0][0]['text'], "🚀 Apply Now")
        self.assertEqual(data['inline_keyboard'][0][0]['url'], "https://example.com/job/42")

        # Second row: Contacted + Irrelevant
        self.assertEqual(data['inline_keyboard'][1][0]['callback_data'], "contacted:42")
        self.assertEqual(data['inline_keyboard'][1][1]['callback_data'], "reject:42")

    def test_keyboard_json(self):
        """Test keyboard serialization"""
        from leads.bot.keyboards import get_lead_keyboard
        import json

        keyboard = get_lead_keyboard(1, "https://example.com")
        json_str = keyboard.to_json()
        parsed = json.loads(json_str)

        self.assertIn('inline_keyboard', parsed)


class DemoScraperTests(TestCase):
    """Phase 1: Test demo scraper"""

    def test_demo_scraper_output_format(self):
        """Test that DemoScraper returns properly formatted leads"""
        from leads.scraper.base import DemoScraper

        scraper = DemoScraper(headless=True, max_pages=1)
        leads = asyncio.run(scraper.scrape())

        self.assertIsInstance(leads, list)
        self.assertGreater(len(leads), 0)

        # Check lead format
        lead = leads[0]
        self.assertIn('title', lead)
        self.assertIn('url', lead)
        self.assertIn('budget', lead)
        self.assertIn('tech_stack', lead)
        self.assertIn('source', lead)
        self.assertIn('content_hash', lead)

        # Content hash should be SHA-256
        self.assertEqual(len(lead['content_hash']), 64)

    def test_demo_scraper_source_name(self):
        """Test demo scraper source"""
        from leads.scraper.base import DemoScraper
        scraper = DemoScraper()
        self.assertEqual(scraper.source_name, 'demo')
