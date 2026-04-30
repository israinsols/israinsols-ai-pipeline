"""
Israinsols Pipeline - Base Scraper (Phase 1)

Abstract base class for all scrapers.
Har naye source (Upwork, Freelancer, Agency) ke liye
is class ko inherit kar ke apna scraper banao.
"""
import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .stealth import create_stealth_browser, safe_goto, random_delay, human_like_scroll

logger = logging.getLogger('leads.scraper')


class BaseScraper(ABC):
    """
    Abstract Base Scraper — har scraper is class ko inherit karega.

    Subclass mein yeh methods implement karne hain:
    - get_target_url(): Target page ka URL return karo
    - parse_page(page): Page se raw data extract karo
    - transform_lead(raw): Raw data ko standardized format mein convert karo

    Usage:
        scraper = UpworkScraper()
        leads = await scraper.scrape()
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        max_pages: int = 3,
        delay_min: float = 2.0,
        delay_max: float = 7.0,
    ):
        self.headless = headless
        self.proxy = proxy
        self.max_pages = max_pages
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.source_name = 'unknown'

    @abstractmethod
    def get_target_url(self, page_num: int = 1) -> str:
        """Return the URL to scrape for a given page number"""
        pass

    @abstractmethod
    async def parse_page(self, page) -> List[Dict[str, Any]]:
        """
        Extract raw lead data from the current page.
        Must return a list of dicts with at least: title, url
        """
        pass

    def transform_lead(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw scraped data into standardized lead format.
        Override this in subclass if needed.
        """
        title = raw.get('title', '').strip()
        url = raw.get('url', '').strip()

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(
            f"{title.lower()}|{url.lower()}".encode()
        ).hexdigest()

        return {
            'title': title,
            'description': raw.get('description', '').strip(),
            'budget': raw.get('budget', '').strip(),
            'tech_stack': raw.get('tech_stack', []),
            'url': url,
            'source': self.source_name,
            'client_name': raw.get('client_name', '').strip(),
            'client_country': raw.get('client_country', '').strip(),
            'posted_date': raw.get('posted_date', '').strip(),
            'content_hash': content_hash,
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method — orchestrates the full flow:
        1. Browser launch (stealth mode)
        2. Navigate to target URLs
        3. Parse data from each page
        4. Transform into standardized format
        5. Return list of leads

        Returns:
            List of lead dicts ready to be saved to database
        """
        all_leads = []
        start_time = time.time()

        logger.info(f"🚀 Starting {self.source_name} scraper (max {self.max_pages} pages)")

        try:
            async with create_stealth_browser(
                headless=self.headless,
                proxy=self.proxy,
            ) as (browser, context, page):

                for page_num in range(1, self.max_pages + 1):
                    url = self.get_target_url(page_num)
                    logger.info(f"📄 Scraping page {page_num}: {url}")

                    # Navigate to page
                    success = await safe_goto(page, url)
                    if not success:
                        logger.warning(f"⚠️ Failed to load page {page_num}, skipping")
                        continue

                    # Simulate human browsing
                    await human_like_scroll(page)
                    await random_delay(self.delay_min, self.delay_max)

                    # Parse leads from page
                    try:
                        raw_leads = await self.parse_page(page)
                        logger.info(f"  Found {len(raw_leads)} leads on page {page_num}")
                    except Exception as e:
                        logger.error(f"  ❌ Parse error on page {page_num}: {e}")
                        raw_leads = []

                    # Transform each lead
                    for raw in raw_leads:
                        try:
                            lead = self.transform_lead(raw)
                            if lead.get('title') and lead.get('url'):
                                all_leads.append(lead)
                        except Exception as e:
                            logger.warning(f"  Transform error: {e}")

                    # Random delay between pages
                    if page_num < self.max_pages:
                        await random_delay(self.delay_min * 1.5, self.delay_max * 1.5)

        except Exception as e:
            logger.error(f"❌ Scraper crashed: {e}")
            raise

        elapsed = time.time() - start_time
        logger.info(
            f"✅ {self.source_name} scraper done | "
            f"{len(all_leads)} leads | {elapsed:.1f}s elapsed"
        )

        return all_leads


class DemoScraper(BaseScraper):
    """
    Demo scraper for testing — generates fake leads.
    Use this for development and testing without hitting real websites.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source_name = 'demo'

    def get_target_url(self, page_num: int = 1) -> str:
        return f"https://httpbin.org/html?page={page_num}"

    async def parse_page(self, page) -> List[Dict[str, Any]]:
        """Generate demo leads for testing"""
        import random

        demo_titles = [
            "Full Stack Developer Needed for SaaS Platform",
            "React Native Mobile App Development",
            "WordPress E-commerce Website Redesign",
            "Python Django REST API Development",
            "Node.js Microservices Architecture",
            "Vue.js Frontend for Dashboard Application",
            "AWS Cloud Infrastructure Setup",
            "Machine Learning Model Integration",
            "Shopify Custom Theme Development",
            "Flutter Cross-Platform App",
            "Laravel PHP Backend Development",
            "Angular Enterprise Application",
            "PostgreSQL Database Optimization",
            "DevOps CI/CD Pipeline Setup",
            "Blockchain Smart Contract Development",
        ]

        demo_tech_stacks = [
            ["React", "Node.js", "PostgreSQL"],
            ["Python", "Django", "Redis"],
            ["Vue.js", "Laravel", "MySQL"],
            ["React Native", "Firebase"],
            ["WordPress", "WooCommerce", "PHP"],
            ["Flutter", "Dart", "Firebase"],
            ["Angular", "TypeScript", ".NET"],
            ["Next.js", "Tailwind CSS", "Prisma"],
            ["AWS", "Docker", "Kubernetes"],
            ["Solidity", "Web3.js", "Ethereum"],
        ]

        demo_budgets = [
            "$100 - $500", "$500 - $1,000", "$1,000 - $2,500",
            "$2,500 - $5,000", "$5,000 - $10,000", "$10,000+",
            "Hourly: $25 - $50/hr", "Hourly: $50 - $100/hr",
        ]

        demo_countries = [
            "United States", "United Kingdom", "Canada", "Germany",
            "Australia", "UAE", "Saudi Arabia", "Netherlands",
        ]

        leads = []
        num_leads = random.randint(3, 8)

        for i in range(num_leads):
            title = random.choice(demo_titles)
            leads.append({
                'title': f"{title} #{random.randint(1000, 9999)}",
                'description': f"We need an experienced developer for {title.lower()}. "
                              f"This is a {'fixed-price' if random.random() > 0.5 else 'hourly'} project.",
                'budget': random.choice(demo_budgets),
                'tech_stack': random.choice(demo_tech_stacks),
                'url': f"https://demo.example.com/jobs/{random.randint(100000, 999999)}",
                'client_name': f"Client_{random.randint(100, 999)}",
                'client_country': random.choice(demo_countries),
                'posted_date': 'Just now',
            })

        return leads
