"""
Israinsols Pipeline - Celery Application Configuration

Yeh file Celery app ko configure karti hai. Celery ek distributed task queue
hai jo background mein heavy jobs (jaise scraping) run karta hai taake
Django server freeze na ho.
"""
import os
from celery import Celery

# Django settings module set karo
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery app create karo
app = Celery('israinsols')

# Django settings se Celery config load karo (CELERY_ prefix wali settings)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
# Yeh 'leads/tasks.py' ko automatically find karega
app.autodiscover_tasks()


# ──────────────────────────────────────────────
# Periodic Tasks (Beat Schedule)
# Yeh tasks automatically schedule par run honge
# ──────────────────────────────────────────────
app.conf.beat_schedule = {

    # ── Fiverr scrapers — multiple search queries, staggered timing ──────────
    'fiverr-web-development': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 1800.0,   # every 30 min
        'args': ('fiverr',),
        'kwargs': {'search_query': 'web development', 'max_pages': 2},
        'options': {'queue': 'scraping'},
    },
    'fiverr-python-developer': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 1800.0,
        'args': ('fiverr',),
        'kwargs': {'search_query': 'python developer', 'max_pages': 2},
        'options': {'queue': 'scraping'},
    },
    'fiverr-django-developer': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 3600.0,   # every 1 hour
        'args': ('fiverr',),
        'kwargs': {'search_query': 'django developer', 'max_pages': 2},
        'options': {'queue': 'scraping'},
    },
    'fiverr-react-developer': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 3600.0,
        'args': ('fiverr',),
        'kwargs': {'search_query': 'react developer', 'max_pages': 2},
        'options': {'queue': 'scraping'},
    },
    'freelancer-python-django': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 3600.0,
        'args': ('freelancer',),
        'kwargs': {'search_query': 'python django', 'max_results': 50},
        'options': {'queue': 'scraping'},
    },
    'freelancer-web-scraping': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 5400.0,
        'args': ('freelancer',),
        'kwargs': {'search_query': 'web scraping', 'max_results': 50},
        'options': {'queue': 'scraping'},
    },
    'freelancer-react-developer': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 3600.0,
        'args': ('freelancer',),
        'kwargs': {'search_query': 'react developer', 'max_results': 50},
        'options': {'queue': 'scraping'},
    },
    'freelancer-mobile-app': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 7200.0,  # every 2 hours
        'args': ('freelancer',),
        'kwargs': {'search_query': 'mobile app development', 'max_results': 50},
        'options': {'queue': 'scraping'},
    },
    'freelancer-shopify-developer': {
        'task': 'leads.tasks.run_scraper_task',
        'schedule': 5400.0,
        'args': ('freelancer',),
        'kwargs': {'search_query': 'shopify developer', 'max_results': 50},
        'options': {'queue': 'scraping'},
    },

    # ── Telegram alerts — send unnotified leads every 5 min ─────────────────
    'send-alerts-every-5-minutes': {
        'task': 'leads.tasks.send_unnotified_alerts_task',
        'schedule': 300.0,
        'options': {'queue': 'alerts'},
    },

    # ── Weekly cleanup ────────────────────────────────────────────────────────
    'cleanup-old-leads-weekly': {
        'task': 'leads.tasks.cleanup_old_leads',
        'schedule': 604800.0,  # 7 days
        'options': {'queue': 'default'},
    },
}

# Default queue
app.conf.task_default_queue = 'default'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Test task to verify Celery is working"""
    print(f'Request: {self.request!r}')
