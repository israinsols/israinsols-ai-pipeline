"""
Israinsols Pipeline - Freelancer.com Scraper
════════════════════════════════════════════
Uses Freelancer.com's public REST API — no account, no key needed for basic reads.
Returns REAL CLIENT PROJECT POSTINGS that you can bid on.

API: https://www.freelancer.com/api/projects/0.1/projects/active/
Docs: https://developers.freelancer.com/

Each project contains:
- Title: What the client needs built
- Description: Full requirements
- Budget: Fixed min/max or hourly rate
- Skills: Required technologies
- Client country
- Bid count (how many freelancers bid already)
- Type: fixed / hourly
- Direct URL to bid

Usage:
    python test_freelancer.py
"""
import re
import json
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .base import BaseScraper

logger = logging.getLogger('leads.scraper')


class FreelancerScraper(BaseScraper):
    """
    Scrapes client project postings from Freelancer.com public API.
    No authentication required for basic project listing.
    """

    API_BASE = "https://www.freelancer.com/api/projects/0.1/projects/active/"

    def __init__(
        self,
        search_query: str = "python django web development",
        min_budget: int = 0,
        max_results: int = 50,
        max_pages: int = 1,
        headless: bool = True,   # compatibility only
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.search_query = search_query
        self.min_budget = min_budget
        self.max_results = max_results
        self.max_pages = max_pages
        self.source_name = 'freelancer'

    def get_target_url(self, page_num: int = 1) -> str:
        limit = min(self.max_results, 50)
        offset = (page_num - 1) * limit
        params = {
            'query': self.search_query,
            'job_details': 'true',
            'user_details': 'false',
            'limit': limit,
            'offset': offset,
            'sort_field': 'time_updated',
            'reverse_sort': 'true',
            'compact': 'true',
        }
        return f"{self.API_BASE}?{urlencode(params)}"

    async def parse_page(self, page) -> List[Dict[str, Any]]:
        """Required by ABC — not used."""
        return []

    async def scrape(self) -> List[Dict[str, Any]]:
        """Fetch projects from Freelancer.com public API."""
        url = self.get_target_url()
        logger.info(f"Fetching Freelancer.com projects: {url}")

        try:
            req = Request(
                url,
                headers={
                    'User-Agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'
                    ),
                    'Accept': 'application/json',
                    'Freelancer-Client': 'web',
                }
            )
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

        except HTTPError as e:
            logger.error(f"Freelancer API HTTP error {e.code}: {e.reason}")
            return []
        except URLError as e:
            logger.error(f"Freelancer API connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"Freelancer API error: {e}")
            return []

        if data.get('status') != 'success':
            logger.warning(f"Freelancer API returned: {data.get('message', 'unknown error')}")
            return []

        projects = data.get('result', {}).get('projects', [])
        jobs_data = data.get('result', {}).get('jobs', {})  # skill details

        logger.info(f"Freelancer.com: {len(projects)} projects for '{self.search_query}'")
        return self._parse_projects(projects, jobs_data)

    def _parse_projects(self, projects: list, jobs_data: dict) -> List[Dict[str, Any]]:
        leads = []
        for p in projects:
            try:
                title = p.get('title', '').strip()
                if not title:
                    continue

                pid = p.get('id', '')
                seo_url = p.get('seo_url', '')
                url = f"https://www.freelancer.com/projects/{seo_url}" if seo_url else \
                      f"https://www.freelancer.com/projects/{pid}"

                # Description
                description = p.get('description', '').strip()[:500]

                # Budget
                budget_obj = p.get('budget', {})
                b_min = budget_obj.get('minimum', 0)
                b_max = budget_obj.get('maximum', 0)
                currency = p.get('currency', {}).get('sign', '$')
                job_type = p.get('type', '')  # 'fixed' or 'hourly'

                if b_min and b_max:
                    if job_type == 'hourly':
                        budget = f"Hourly: {currency}{b_min} - {currency}{b_max}/hr"
                    else:
                        budget = f"Fixed: {currency}{b_min} - {currency}{b_max}"
                elif b_min:
                    budget = f"{currency}{b_min}"
                else:
                    budget = ''

                # Skills from job IDs
                job_ids = p.get('jobs', [])
                skills = []
                for jid in job_ids:
                    jid_str = str(jid.get('id', '') if isinstance(jid, dict) else jid)
                    if jid_str in jobs_data:
                        skills.append(jobs_data[jid_str].get('name', ''))
                    elif isinstance(jid, dict):
                        skills.append(jid.get('name', ''))
                skills = [s for s in skills if s][:10]

                # Bid / country info
                bid_count = p.get('bid_stats', {}).get('bid_count', 0)
                country = ''
                owner = p.get('owner', {})
                if isinstance(owner, dict):
                    loc = owner.get('location', {})
                    if isinstance(loc, dict):
                        country = loc.get('country', {}).get('name', '') if isinstance(loc.get('country'), dict) else ''

                # Posted date
                time_submitted = p.get('time_submitted', 0)
                posted_date = ''
                if time_submitted:
                    import datetime
                    posted_date = datetime.datetime.utcfromtimestamp(time_submitted).strftime('%Y-%m-%d %H:%M UTC')

                # Min budget filter
                if self.min_budget and b_max and b_max < self.min_budget:
                    continue

                lead = {
                    'title':          title,
                    'url':            url,
                    'description':    f"{description} [Bids: {bid_count}]",
                    'budget':         budget,
                    'tech_stack':     skills,
                    'source':         'freelancer',
                    'client_country': country,
                    'posted_date':    posted_date,
                    'client_name':    '',
                }
                leads.append(lead)

            except Exception as e:
                logger.warning(f"Error parsing project: {e}")
                continue

        return leads

    def transform_lead(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        lead = super().transform_lead(raw)
        lead['source'] = 'freelancer'
        if lead.get('budget'):
            lead['budget'] = re.sub(r'\s+', ' ', lead['budget']).strip()
        if isinstance(lead.get('tech_stack'), list):
            lead['tech_stack'] = ', '.join(lead['tech_stack'])
        return lead
