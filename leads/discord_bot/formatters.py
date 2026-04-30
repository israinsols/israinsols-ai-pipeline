"""
Israinsols Pipeline - Discord Message Formatter
Converts leads and stats into Discord-friendly Markdown.
"""
import re

def format_lead_message_discord(lead) -> str:
    """
    Format lead for Discord Markdown.
    """
    # Build tech stack display
    tech_display = ''
    if lead.tech_stack:
        if isinstance(lead.tech_stack, list):
            tech_tags = ', '.join(f'`{t}`' for t in lead.tech_stack[:8])
            tech_display = f"\n🛠 **Tech:** {tech_tags}"
        elif isinstance(lead.tech_stack, str) and lead.tech_stack:
            tech_display = f"\n🛠 **Tech:** `{lead.tech_stack}`"

    # Budget display
    budget_display = ''
    if lead.budget:
        budget_display = f"\n💰 **Budget:** {lead.budget}"

    # Client info
    client_display = ''
    if lead.client_country:
        client_display = f"\n🌍 **Client:** {lead.client_country}"
    if lead.client_name:
        client_display += f" ({lead.client_name})"

    # Posted date
    posted_display = ''
    if lead.posted_date:
        posted_display = f"\n📅 **Posted:** {lead.posted_date}"

    # Description preview (first 200 chars)
    desc_display = ''
    if lead.description:
        desc_preview = lead.description[:200].strip()
        if len(lead.description) > 200:
            desc_preview += '...'
        desc_display = f"\n\n> *{desc_preview}*"

    # High value badge
    value_badge = ''
    if hasattr(lead, 'is_high_value') and lead.is_high_value:
        value_badge = ' 💎'

    # Source display
    source_name = lead.get_source_display() if hasattr(lead, 'get_source_display') else lead.source

    message = (
        f"🔥 **New Lead Found!**{value_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📋 **Title:** {lead.title}"
        f"{budget_display}"
        f"{tech_display}"
        f"{posted_display}"
        f"{client_display}\n"
        f"🔗 **Source:** [{source_name}]({lead.url})\n"
        f"📍 **Job Link:** {lead.url}"
        f"{desc_display}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Lead #{lead.id}"
    )

    return message

def format_stats_message_discord(stats: dict) -> str:
    """Format pipeline statistics for Discord"""
    return (
        f"📊 **Israinsols Pipeline Stats**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📋 **Total Leads:** {stats.get('total', 0)}\n"
        f"🔵 **Unnotified:** {stats.get('unnotified', 0)}\n"
        f"🟡 **Notified:** {stats.get('notified', 0)}\n"
        f"🟢 **Contacted:** {stats.get('contacted', 0)}\n"
        f"🟣 **Applied:** {stats.get('applied', 0)}\n"
        f"🔴 **Rejected:** {stats.get('rejected', 0)}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 **Today:** {stats.get('today', 0)} new leads\n"
        f"📅 **This Week:** {stats.get('this_week', 0)} new leads\n"
        f"💎 **High Value:** {stats.get('high_value', 0)} leads ($500+)"
    )

def format_agency_welcome_discord() -> str:
    return (
        "🚀 **Welcome to Israinsols!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "We are an elite software agency specializing in **Web Development, SEO, and Digital Growth**.\n"
        "\n"
        "How can we help you today?\n"
        "\n"
        "🔹 **Our Services:** See what we do\n"
        "🔹 **FAQs:** Get instant answers\n"
        "🔹 **Contact Us:** Start your project\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 Powered by Israinsols"
    )

def format_faq_answer_discord(question: str, answer: str) -> str:
    return (
        f"❓ **{question}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"{answer}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "*Was this helpful? Feel free to contact us for more details!*"
    )
