"""
Israinsols Pipeline - Lead Message Formatter (Phase 4)

Leads ko beautiful HTML format mein convert karta hai
Telegram messages ke liye. Plain text nahi — proper formatting!
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from leads.models import ScrapedLead


def format_lead_message(lead) -> str:
    """
    Lead ko Telegram-friendly HTML message mein format karo.

    Output example:
    🔥 New Lead Found!
    ━━━━━━━━━━━━━━━━━
    📋 Title: React Developer Needed
    💰 Budget: $500 - $1,000
    🛠 Tech: React, Node.js
    📅 Posted: Just now
    🌍 Client: United States
    🔗 Source: Upwork
    ━━━━━━━━━━━━━━━━━
    """
    # Build tech stack display
    tech_display = ''
    if lead.tech_stack:
        if isinstance(lead.tech_stack, list):
            tech_tags = ', '.join(f'<code>{t}</code>' for t in lead.tech_stack[:8])
            tech_display = f"\n🛠 <b>Tech:</b> {tech_tags}"
        elif isinstance(lead.tech_stack, str) and lead.tech_stack:
            tech_display = f"\n🛠 <b>Tech:</b> <code>{lead.tech_stack}</code>"

    # Budget display
    budget_display = ''
    if lead.budget:
        budget_display = f"\n💰 <b>Budget:</b> {_escape_html(lead.budget)}"

    # Client info
    client_display = ''
    if lead.client_country:
        client_display = f"\n🌍 <b>Client:</b> {_escape_html(lead.client_country)}"
    if lead.client_name:
        client_display += f" ({_escape_html(lead.client_name)})"

    # Posted date
    posted_display = ''
    if lead.posted_date:
        posted_display = f"\n📅 <b>Posted:</b> {_escape_html(lead.posted_date)}"

    # Description preview (first 200 chars)
    desc_display = ''
    if lead.description:
        desc_preview = lead.description[:200].strip()
        if len(lead.description) > 200:
            desc_preview += '...'
        desc_display = f"\n\n📝 <i>{_escape_html(desc_preview)}</i>"

    # High value badge
    value_badge = ''
    if hasattr(lead, 'is_high_value') and lead.is_high_value:
        value_badge = ' 💎'

    # Source display
    source_name = lead.get_source_display() if hasattr(lead, 'get_source_display') else lead.source

    message = (
        f"🔥 <b>New Lead Found!</b>{value_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📋 <b>Title:</b> {_escape_html(lead.title)}"
        f"{budget_display}"
        f"{tech_display}"
        f"{posted_display}"
        f"{client_display}\n"
        f"🔗 <b>Source:</b> <a href='{lead.url}'>{_escape_html(source_name)}</a>\n"
        f"📍 <b>Job Link:</b> {lead.url}"
        f"{desc_display}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Lead #{lead.id}"
    )

    return message


def format_lead_updated_message(lead, new_status: str) -> str:
    """Format message for when a lead's status is updated via button click"""
    status_emojis = {
        'contacted': '✅',
        'rejected': '❌',
        'applied': '🟣',
    }
    emoji = status_emojis.get(new_status, '📝')

    return (
        f"{emoji} <b>Lead Updated!</b>\n"
        f"\n"
        f"📋 {_escape_html(lead.title[:80])}\n"
        f"📊 Status: <b>{new_status.upper()}</b>\n"
        f"⏰ Updated: {lead.updated_at.strftime('%Y-%m-%d %H:%M') if lead.updated_at else 'N/A'}"
    )


def format_stats_message(stats: dict) -> str:
    """Format pipeline statistics for /stats command"""
    return (
        f"📊 <b>Israinsols Pipeline Stats</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📋 <b>Total Leads:</b> {stats.get('total', 0)}\n"
        f"🔵 <b>Unnotified:</b> {stats.get('unnotified', 0)}\n"
        f"🟡 <b>Notified:</b> {stats.get('notified', 0)}\n"
        f"🟢 <b>Contacted:</b> {stats.get('contacted', 0)}\n"
        f"🟣 <b>Applied:</b> {stats.get('applied', 0)}\n"
        f"🔴 <b>Rejected:</b> {stats.get('rejected', 0)}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>Today:</b> {stats.get('today', 0)} new leads\n"
        f"📅 <b>This Week:</b> {stats.get('this_week', 0)} new leads\n"
        f"💎 <b>High Value:</b> {stats.get('high_value', 0)} leads ($500+)"
    )



def format_agency_welcome_message() -> str:
    """Welcome message for the agency bot flow."""
    return (
        "🚀 <b>Welcome to Israinsols!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "We are an elite software agency specializing in <b>Web Development, SEO, and Digital Growth</b>.\n"
        "\n"
        "How can we help you today?\n"
        "\n"
        "🔹 <b>Our Services:</b> See what we do\n"
        "🔹 <b>FAQs:</b> Get instant answers\n"
        "🔹 <b>Contact Us:</b> Start your project\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 Powered by Israinsols"
    )


def format_faq_answer_message(question: str, answer: str) -> str:
    """Format an FAQ question and answer."""
    return (
        f"❓ <b>{_escape_html(question)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"{_escape_html(answer)}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Was this helpful? Feel free to contact us for more details!</i>"
    )


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram"""
    if not text:
        return ''
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
