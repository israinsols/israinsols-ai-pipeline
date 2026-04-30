"""
Israinsols Pipeline - Database Models (Phase 2)

ScrapedLead Model:
- Har scraped lead ka record store karta hai
- Duplicate detection URL ke basis par (unique constraint)
- Status tracking: Unnotified → Notified → Contacted/Rejected
- Indexes for fast querying on status, source, url
"""
import hashlib
from django.db import models
from django.utils import timezone


class ScrapedLead(models.Model):
    """
    Represents a single scraped lead from Freelancer.com.

    Workflow:
    1. Scraper finds new job/lead → saves with status UNNOTIFIED
    2. Bot picks up UNNOTIFIED leads → sends to Telegram → status becomes NOTIFIED
    3. User clicks button → status becomes CONTACTED or REJECTED
    """

    class Status(models.TextChoices):
        UNNOTIFIED = 'unnotified', '🔵 Unnotified'
        NOTIFIED = 'notified', '🟡 Notified'
        CONTACTED = 'contacted', '🟢 Contacted'
        REJECTED = 'rejected', '🔴 Rejected'
        APPLIED = 'applied', '🟣 Applied'

    class Source(models.TextChoices):
        FREELANCER = 'freelancer', 'Freelancer.com'
        OTHER = 'other', 'Other'

    # ──────────────────────────────────────────
    # Core Lead Information
    # ──────────────────────────────────────────
    title = models.CharField(
        max_length=500,
        help_text="Job title or lead heading"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Full job description or details"
    )
    budget = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Client budget range, e.g. '$500 - $1,000'"
    )
    tech_stack = models.JSONField(
        default=list,
        blank=True,
        help_text="List of technologies, e.g. ['React', 'Node.js', 'PostgreSQL']"
    )
    url = models.URLField(
        max_length=2000,
        unique=True,
        help_text="Direct URL to the job posting or lead page"
    )
    source = models.CharField(
        max_length=50,
        choices=Source.choices,
        default=Source.OTHER,
        help_text="Where this lead was scraped from"
    )
    client_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Client or company name (if available)"
    )
    client_country = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Client location/country"
    )
    posted_date = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="When the job was posted (as displayed on source)"
    )

    # ──────────────────────────────────────────
    # Status & Tracking
    # ──────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNNOTIFIED,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Internal notes about this lead"
    )
    telegram_message_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Telegram message ID for updating the sent alert"
    )

    # ──────────────────────────────────────────
    # Deduplication
    # ──────────────────────────────────────────
    content_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        help_text="SHA-256 hash of title+url for deduplication"
    )

    # ──────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────
    scraped_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scraped_at']
        verbose_name = 'Scraped Lead'
        verbose_name_plural = 'Scraped Leads'
        indexes = [
            models.Index(fields=['status'], name='idx_lead_status'),
            models.Index(fields=['source'], name='idx_lead_source'),
            models.Index(fields=['scraped_at'], name='idx_lead_scraped_at'),
            models.Index(fields=['status', 'source'], name='idx_lead_status_source'),
        ]

    def __str__(self):
        return f"[{self.get_source_display()}] {self.title[:80]}"

    def save(self, *args, **kwargs):
        """Auto-generate content_hash before saving for deduplication"""
        if not self.content_hash:
            raw = f"{self.title.strip().lower()}|{self.url.strip().lower()}"
            self.content_hash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    @property
    def tech_stack_display(self) -> str:
        """Comma-separated tech stack for display"""
        if isinstance(self.tech_stack, list):
            return ', '.join(self.tech_stack)
        return str(self.tech_stack)

    @property
    def is_high_value(self) -> bool:
        """Check if budget suggests a high-value lead"""
        if not self.budget:
            return False
        # Try to extract numbers from budget string
        import re
        numbers = re.findall(r'[\d,]+', self.budget.replace(',', ''))
        if numbers:
            max_budget = max(int(n) for n in numbers if n.isdigit())
            return max_budget >= 500
        return False

    def mark_as_notified(self):
        """Mark lead as notified (bot ne message bhej diya)"""
        self.status = self.Status.NOTIFIED
        self.notified_at = timezone.now()
        self.save(update_fields=['status', 'notified_at', 'updated_at'])

    def mark_as_contacted(self):
        """User ne 'Contacted' button press kiya"""
        self.status = self.Status.CONTACTED
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_rejected(self):
        """User ne 'Irrelevant' button press kiya"""
        self.status = self.Status.REJECTED
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_applied(self):
        """User ne 'Applied' button press kiya"""
        self.status = self.Status.APPLIED
        self.save(update_fields=['status', 'updated_at'])


class ScrapeLog(models.Model):
    """
    Har scraping run ka log rakhta hai — monitoring ke liye
    Admin panel mein dekh sakte hain ke scraper theek se chal raha hai ya nahi
    """

    class RunStatus(models.TextChoices):
        SUCCESS = 'success', '✅ Success'
        PARTIAL = 'partial', '⚠️ Partial'
        FAILED = 'failed', '❌ Failed'

    source = models.CharField(max_length=50)
    run_status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.SUCCESS,
    )
    total_found = models.IntegerField(default=0, help_text="Total leads found in this run")
    new_saved = models.IntegerField(default=0, help_text="New leads saved (after dedup)")
    duplicates_skipped = models.IntegerField(default=0, help_text="Duplicates that were skipped")
    error_message = models.TextField(blank=True, default='')
    duration_seconds = models.FloatField(default=0.0)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Scrape Log'
        verbose_name_plural = 'Scrape Logs'

    def __str__(self):
        return f"[{self.run_status}] {self.source} @ {self.started_at:%Y-%m-%d %H:%M}"

class FAQ(models.Model):
    """
    Frequently Asked Questions managed via Django Admin.
    Displayed in the Telegram bot.
    """
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Services, Pricing, Technical")
    order = models.IntegerField(default=0, help_text="Sorting order (lower numbers first)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question[:100]


class AgencyLead(models.Model):
    """
    Leads collected directly from the Telegram bot (Contact Us flow).
    """
    class Status(models.TextChoices):
        NEW = 'new', '🆕 New'
        CONTACTED = 'contacted', '✅ Contacted'
        QUALIFIED = 'qualified', '💎 Qualified'
        LOST = 'lost', '❌ Lost'

    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    service_interested = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agency Lead'
        verbose_name_plural = 'Agency Leads'

    def __str__(self):
        return f"{self.full_name} - {self.service_interested or 'General Query'}"
