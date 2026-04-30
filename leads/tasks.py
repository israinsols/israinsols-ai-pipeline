"""
Israinsols Pipeline - Celery Tasks (Phase 3)

Background tasks jo automatically schedule par run hote hain:
1. run_scraper_task: Har 15 min scraper chalata hai
2. send_unnotified_alerts_task: Unnotified leads Telegram par bhejta hai

Celery + Redis use karta hai — Django server freeze nahi hoga.
"""
import asyncio
import logging
import time
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError

logger = logging.getLogger('leads')


def _save_new_leads(leads_data: list) -> dict:
    """
    Naye leads ko database mein save karo.
    Duplicates automatically skip ho jayengi (URL + content_hash unique constraint).

    Returns:
        dict with counts: {'total': N, 'saved': N, 'duplicates': N}
    """
    from leads.models import ScrapedLead

    saved = 0
    duplicates = 0
    saved_leads = []

    for lead_data in leads_data:
        try:
            # Check if lead already exists (by URL or content_hash)
            exists = ScrapedLead.objects.filter(
                url=lead_data['url']
            ).exists()

            if exists:
                duplicates += 1
                continue

            # Create new lead
            lead = ScrapedLead(
                title=lead_data['title'],
                description=lead_data.get('description', ''),
                budget=lead_data.get('budget', ''),
                tech_stack=lead_data.get('tech_stack', []),
                url=lead_data['url'],
                source=lead_data.get('source', 'other'),
                client_name=lead_data.get('client_name', ''),
                client_country=lead_data.get('client_country', ''),
                posted_date=lead_data.get('posted_date', ''),
                content_hash=lead_data.get('content_hash', ''),
                status=ScrapedLead.Status.UNNOTIFIED,
            )
            lead.save()
            saved_leads.append(lead)
            saved += 1
            logger.info(f"  💾 Saved: {lead.title[:60]}")

        except IntegrityError:
            duplicates += 1
        except Exception as e:
            if "async context" in str(e).lower():
                logger.error(f"  ⚠️ Async context detected. Lead '{lead_data['title'][:40]}' skipped for now.")
            else:
                logger.error(f"  ❌ Error saving lead: {e}")

    # Send immediate alerts for newly saved leads
    if saved_leads:
        logger.info(f"  📨 Sending {len(saved_leads)} immediate alerts...")
        for lead in saved_leads:
            try:
                success = _send_single_alert_sync(lead)
                if success:
                    lead.mark_as_notified()
                    logger.info(f"    ✅ Alert sent: {lead.title[:50]}")
                else:
                    logger.warning(f"    ❌ Alert failed: {lead.title[:50]}")
            except Exception as e:
                logger.error(f"    ❌ Error sending alert for {lead.id}: {e}")

    return {
        'total': len(leads_data),
        'saved': saved,
        'duplicates': duplicates,
    }


def _log_scrape_run(source: str, result: dict, duration: float, error: str = ''):
    """Save scrape run log for monitoring"""
    from leads.models import ScrapeLog

    status = ScrapeLog.RunStatus.SUCCESS
    if error:
        status = ScrapeLog.RunStatus.FAILED
    elif result.get('saved', 0) == 0 and result.get('total', 0) > 0:
        status = ScrapeLog.RunStatus.PARTIAL

    ScrapeLog.objects.create(
        source=source,
        run_status=status,
        total_found=result.get('total', 0),
        new_saved=result.get('saved', 0),
        duplicates_skipped=result.get('duplicates', 0),
        error_message=error,
        duration_seconds=duration,
    )


# ──────────────────────────────────────────────────────
# CELERY TASK 1: Run Scraper (Har 15 min)
# ──────────────────────────────────────────────────────
@shared_task(
    bind=True,
    name='leads.tasks.run_scraper_task',
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
)
def run_scraper_task(self, search_query: str = 'web development', **kwargs):
    """
    Background Celery task — Freelancer.com scraper chalata hai.

    Args:
        search_query: Search term (e.g., 'react developer')
        **kwargs: Extra arguments: max_results, min_budget, etc.
    """
    start_time = time.time()
    source = 'freelancer'
    result = {'total': 0, 'saved': 0, 'duplicates': 0}
    error_msg = ''

    logger.info(f"🤖 Celery Task Started: Freelancer Scraper for '{search_query}'")

    try:
        from leads.scraper.freelancer import FreelancerScraper
        
        scraper = FreelancerScraper(
            search_query=search_query,
            min_budget=kwargs.pop('min_budget', 0),
            max_results=kwargs.pop('max_results', 50),
            **kwargs,
        )

        # Run the async scraper
        leads_data = asyncio.run(scraper.scrape())

        # Save leads to database
        result = _save_new_leads(leads_data)

        logger.info(
            f"✅ Scraper done | Found: {result['total']} | "
            f"New: {result['saved']} | Dups: {result['duplicates']}"
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"❌ Freelancer scraper task failed: {error_msg}")

        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc)
        raise

    finally:
        duration = time.time() - start_time
        _log_scrape_run(source, result, duration, error_msg)

    return {
        'status': 'success',
        'source': source,
        'total_found': result['total'],
        'new_saved': result['saved'],
        'duplicates_skipped': result['duplicates'],
        'duration_seconds': round(duration, 1),
    }



# ──────────────────────────────────────────────────────
# CELERY TASK 2: Send Telegram Alerts (Har 5 min)
# ──────────────────────────────────────────────────────
@shared_task(
    bind=True,
    name='leads.tasks.send_unnotified_alerts_task',
    max_retries=2,
    default_retry_delay=60,
    time_limit=120,
)
def send_unnotified_alerts_task(self, batch_size: int = 5):
    """
    Unnotified leads pick karo aur Telegram par bhejo.
    Ek batch mein max 5 leads process karta hai (rate limiting ke liye).

    Args:
        batch_size: Maximum leads to send in one batch
    """
    from leads.models import ScrapedLead

    logger.info("📨 Checking for unnotified leads...")

    # Get unnotified leads (oldest first, limited batch)
    leads = ScrapedLead.objects.filter(
        status=ScrapedLead.Status.UNNOTIFIED
    ).order_by('scraped_at')[:batch_size]

    if not leads:
        logger.info("  No unnotified leads found.")
        return {'sent': 0, 'message': 'No unnotified leads'}

    sent_count = 0
    for lead in leads:
        try:
            # Send Telegram alert (sync — no asyncio needed)
            success = _send_single_alert_sync(lead)

            if success:
                lead.mark_as_notified()
                sent_count += 1
                logger.info(f"  📬 Alert sent for: {lead.title[:50]}")
            else:
                logger.warning(f"  ⚠️ Failed to send alert for lead {lead.id}")

        except Exception as e:
            logger.error(f"  ❌ Error sending alert for lead {lead.id}: {e}")

    logger.info(f"📨 Alerts done: {sent_count}/{len(leads)} sent")
    return {'sent': sent_count, 'total': len(leads)}

def _send_single_alert_sync(lead) -> bool:
    """Send alert to all configured channels (Telegram, Discord, etc.)"""
    tg_success = _send_telegram_alert_sync(lead)
    ds_success = _send_discord_alert_sync(lead)
    
    # Consider overall success if at least one channel worked
    return tg_success or ds_success

def _send_telegram_alert_sync(lead) -> bool:
    """Send a single lead alert via Telegram — SYNC version"""
    try:
        from leads.bot.formatters import format_lead_message
        from leads.bot.keyboards import get_lead_keyboard
        import urllib.request
        import urllib.error
        import json as _json

        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        api_base = getattr(settings, 'TELEGRAM_API_BASE_URL', 'https://api.telegram.org')

        if not token or not chat_id:
            logger.error("Telegram credentials not configured!")
            return False

        # Format message (safe — no async context issues)
        message = format_lead_message(lead)
        keyboard = get_lead_keyboard(lead.id, lead.url)

        # Build request
        url = f"{api_base}/bot{token}/sendMessage"
        payload = _json.dumps({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'reply_markup': _json.loads(keyboard.to_json()) if hasattr(keyboard, 'to_json') else {},
            'disable_web_page_preview': False,
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode('utf-8'))
                if data.get('ok'):
                    msg_id = data.get('result', {}).get('message_id')
                    if msg_id:
                        lead.telegram_message_id = msg_id
                        lead.save(update_fields=['telegram_message_id'])
                    return True
                else:
                    logger.error(f"Telegram API error: {data}")
                    return False
        except urllib.error.URLError as e:
            logger.error(
                f"Cannot connect to Telegram API: {e}\n"
                "  → Telegram is likely blocked by your ISP.\n"
                "  → Fix: Set TELEGRAM_API_BASE_URL in .env to a Cloudflare Worker URL\n"
                "  → Deploy telegram_cf_worker.js to Cloudflare (FREE)\n"
                "  → Or use a VPN/proxy."
            )
            return False
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Telegram HTTP error {e.code}: {error_body}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


def _send_discord_alert_sync(lead) -> bool:
    """Send a single lead alert via Discord — SYNC version"""
    try:
        from leads.discord_bot.formatters import format_lead_message_discord
        import urllib.request
        import urllib.error
        import json as _json

        token = settings.DISCORD_BOT_TOKEN
        channel_id = settings.DISCORD_CHANNEL_ID

        if not token or not channel_id or token == 'your-discord-bot-token':
            return False

        message = format_lead_message_discord(lead)
        
        # Build components (buttons) JSON directly for the API
        # Style 5 is Link, 3 is Success (Green), 4 is Danger (Red)
        components = [
            {
                "type": 1,
                "components": [
                    {"type": 2, "label": "🚀 Apply Now", "style": 5, "url": lead.url},
                ]
            },
            {
                "type": 1,
                "components": [
                    {"type": 2, "label": "✅ Contacted", "style": 3, "custom_id": f"contacted:{lead.id}"},
                    {"type": 2, "label": "❌ Irrelevant", "style": 4, "custom_id": f"reject:{lead.id}"},
                ]
            }
        ]

        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        payload = _json.dumps({
            "content": message,
            "components": components
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Authorization': f'Bot {token}',
                'Content-Type': 'application/json',
                'User-Agent': 'IsrainsolsBot/1.0'
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status in (200, 201)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Discord HTTP error {e.code}: {error_body}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False


async def _send_single_alert(lead) -> bool:
    """Async wrapper — calls sync version (Django ORM safe)"""
    return _send_single_alert_sync(lead)


# ──────────────────────────────────────────────────────
# CELERY TASK 3: Cleanup Old Rejected Leads (Weekly)
# ──────────────────────────────────────────────────────
@shared_task(name='leads.tasks.cleanup_old_leads')
def cleanup_old_leads(days: int = 30):
    """
    30 din se purani rejected leads delete karo.
    Database size manageable rakhne ke liye.
    """
    from leads.models import ScrapedLead

    cutoff = timezone.now() - timezone.timedelta(days=days)
    old_leads = ScrapedLead.objects.filter(
        status=ScrapedLead.Status.REJECTED,
        updated_at__lt=cutoff,
    )

    count = old_leads.count()
    old_leads.delete()
    logger.info(f"🗑️ Cleaned up {count} old rejected leads (older than {days} days)")
    return {'deleted': count}
