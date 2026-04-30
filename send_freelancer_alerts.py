"""
Send unnotified Freelancer leads to Telegram.
Usage: python send_freelancer_alerts.py
"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.models import ScrapedLead
from leads.tasks import _send_single_alert_sync


def main():
    leads = ScrapedLead.objects.filter(
        status=ScrapedLead.Status.UNNOTIFIED,
        source=ScrapedLead.Source.FREELANCER,
    ).order_by('scraped_at')

    total = leads.count()
    print(f"Sending {total} unnotified Freelancer leads to Telegram...\n")

    sent = failed = 0
    for i, lead in enumerate(leads, 1):
        print(f"[{i}/{total}] {lead.title[:60]}")
        success = _send_single_alert_sync(lead)
        if success:
            lead.mark_as_notified()
            sent += 1
            print(f"  ✅ Sent | Budget: {lead.budget or 'No budget'}")
        else:
            failed += 1
            print(f"  ❌ Failed")

        if i < total:
            time.sleep(1)

    print(f"\n{'='*50}")
    print(f"Done! Sent: {sent} | Failed: {failed} | Total: {total}")


if __name__ == '__main__':
    main()
