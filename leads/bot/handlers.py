"""
Israinsols Pipeline - Telegram Bot Handlers (Phase 4)

Main bot file — aiogram 3.x use karta hai.
Handles:
- /start, /help, /stats, /scrape commands
- Inline button callbacks (Contacted, Rejected, Applied, Undo)
- Lead status updates in database

Usage:
    python manage.py run_bot
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import logging
import asyncio
from datetime import timedelta

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from asgiref.sync import sync_to_async

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.filters import Command, CommandStart
from openai import OpenAI

from leads.bot.formatters import (
    format_lead_message, format_lead_updated_message, format_stats_message,
    format_agency_welcome_message, format_faq_answer_message
)
from leads.bot.keyboards import (
    get_lead_keyboard, get_status_updated_keyboard,
    get_agency_main_keyboard, get_services_keyboard, get_faq_list_keyboard, get_faq_answer_keyboard
)

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ---------- FAQ Cache ----------
_faq_cache = {
    'data': None,
    'last_updated': 0
}

async def get_cached_faqs():
    import time
    now = time.time()
    if _faq_cache['data'] is None or now - _faq_cache['last_updated'] > 300:
        # Refresh cache every 5 minutes
        faqs = await sync_to_async(lambda: list(FAQ.objects.filter(is_active=True).values('id', 'question', 'answer', 'category')))()
        _faq_cache['data'] = faqs
        _faq_cache['last_updated'] = now
    return _faq_cache['data']


# ---------- STATES ----------
class ContactForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_service = State()
    waiting_for_message = State()


from leads.models import ScrapedLead, FAQ, AgencyLead

logger = logging.getLogger('leads.bot')

router = Router(name='leads_bot')

# ---------- G0I AI Integration ----------
def get_g0i_client():
    api_key = os.getenv("G0I_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://g0i.shop/v1")

async def generate_negotiation_advice(client_message):
    client = get_g0i_client()
    if not client:
        return "❌ G0I_API_KEY not found in .env"
    
    model = os.getenv("G0I_MODEL", "gpt-4o-a")
    system_prompt = (
        "You are an expert Freelance Sales Manager and Negotiation Coach. Your goal is to help the user "
        "close deals at the best possible rate. \n\n"
        "Analyze the client's message and provide:\n"
        "1. **Strategic Insight**: What is the client's hidden concern? (e.g., price, trust, or timeline)\n"
        "2. **The Perfect Reply**: A professional, persuasive, and tactical response for the user to send.\n"
        "3. **Counter-Offer Tips**: How to handle further objections.\n\n"
        "Tone: Tactical, Professional, and Confident. Use HTML tags (<b>) for formatting."
    )
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Client said: {client_message}"}
            ],
            temperature=0.8
        ))
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ AI Coaching Error: {str(e)}"

async def generate_ai_proposal(text, tone="Professional"):
    client = get_g0i_client()
    if not client:
        return "❌ G0I_API_KEY not found in .env"
    
    model = os.getenv("G0I_MODEL", "gpt-4o-a")
    system_prompt = (
        "You are an elite, high-end freelance proposal writer. Your goal is to write a strictly professional, "
        "persuasive, and concise proposal. \n\n"
        "IMPORTANT RULES:\n"
        "1. DO NOT use markdown headers (like ## or ###). Use **Bold** text for headings instead.\n"
        "2. DO NOT include a sign-off, signature, or placeholders like 'Best regards' or '[Your Name]' at the end. "
        "The system will append the user's official signature automatically.\n"
        "3. Focus on value proposition and solving the client's pain points.\n"
        "4. Tone: Extremely Professional and business-oriented."
    )
    
    try:
        # Run in executor because openai client is sync
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        ))
        proposal = response.choices[0].message.content.strip()
        
        # Remove any lingering "Best regards" or similar if the AI ignores instructions
        if "Best regards" in proposal:
            proposal = proposal.split("Best regards")[0].strip()
        if "Sincerely" in proposal:
            proposal = proposal.split("Sincerely")[0].strip()

        # Append Signature
        signature = (
            "\n\n<b>Best regards,</b>\n"
            "israin Solution\n"
            "03313646645\n"
            "www.israinsols.com"
        )
        return proposal + signature
    except Exception as e:
        return f"❌ AI Error: {str(e)}"


# ---------- Helper async ORM wrappers ----------
async def get_total_leads():
    return await sync_to_async(ScrapedLead.objects.count)()

async def get_leads_by_status():
    return await sync_to_async(lambda: list(ScrapedLead.objects.values('status').annotate(count=Count('id'))))()

async def get_today_leads_count():
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return await sync_to_async(ScrapedLead.objects.filter(scraped_at__gte=today_start).count)()

async def get_week_leads_count():
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    return await sync_to_async(ScrapedLead.objects.filter(scraped_at__gte=week_start).count)()

async def get_high_value_count():
    leads = await sync_to_async(lambda: list(ScrapedLead.objects.exclude(budget='')))()
    return sum(1 for lead in leads if lead.is_high_value)

async def get_recent_leads(limit=5):
    return await sync_to_async(lambda: list(ScrapedLead.objects.all()[:limit]))()

async def get_unnotified_leads(limit=5):
    return await sync_to_async(lambda: list(ScrapedLead.objects.filter(status=ScrapedLead.Status.UNNOTIFIED)[:limit]))()

async def get_unnotified_count():
    return await sync_to_async(ScrapedLead.objects.filter(status=ScrapedLead.Status.UNNOTIFIED).count)()

async def search_leads(keyword, limit=5):
    q = Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(tech_stack__icontains=keyword)
    return await sync_to_async(lambda: list(ScrapedLead.objects.filter(q)[:limit]))()

async def get_search_total(keyword):
    q = Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(tech_stack__icontains=keyword)
    return await sync_to_async(ScrapedLead.objects.filter(q).count)()

async def get_lead_by_id(lead_id):
    return await sync_to_async(ScrapedLead.objects.get)(id=lead_id)

async def update_lead_status(lead, status_field=None, mark_method=None):
    """Generic async update for lead status using method or direct assignment"""
    if mark_method:
        await sync_to_async(getattr(lead, mark_method))()
    elif status_field:
        lead.status = status_field
        await sync_to_async(lead.save)(update_fields=['status', 'updated_at'])
    else:
        raise ValueError("Provide either status_field or mark_method")


# ---------- COMMAND HANDLERS ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = format_agency_welcome_message()
    keyboard = get_agency_main_keyboard()
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.to_aiogram_markup(),
    )


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    welcome_text = format_agency_welcome_message()
    keyboard = get_agency_main_keyboard()
    await callback.message.edit_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.to_aiogram_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "agency_services")
async def callback_services(callback: CallbackQuery):
    text = (
        "💎 <b>Our Core Services</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "• Websites & Web Applications\n"
        "• High-Conversion Landing Pages\n"
        "• Custom Software Development\n"
        "• AI & Automation (n8n, Replit)\n"
        "• Mobile App Development\n"
        "• Bots & Workflow Automation\n"
        "• Speed & Performance Optimization\n"
        "• Code Review, Hosting & Deployment\n"
        "\n"
        "<i>Select a service below to start your project:</i>"
    )
    keyboard = get_services_keyboard()
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.to_aiogram_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_list:"))
async def callback_faq_list(callback: CallbackQuery):
    page = int(callback.data.split(':')[1])
    try:
        faqs = await get_cached_faqs()
        if not faqs:
            await callback.answer("FAQs are temporarily unavailable.", show_alert=True)
            return
        
        text = "❓ <b>Frequently Asked Questions</b>\n<i>Select a question to see the answer:</i>"
        keyboard = get_faq_list_keyboard(faqs, page=page)
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
    except Exception as e:
        logger.error(f"FAQ list error: {e}")
        await callback.answer("Error fetching FAQs.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("faq_view:"))
async def callback_faq_view(callback: CallbackQuery):
    _, faq_id, page = callback.data.split(':')
    faq_id = int(faq_id)
    page = int(page)
    
    try:
        faqs = await get_cached_faqs()
        faq = next((f for f in faqs if f['id'] == faq_id), None)
        
        if not faq:
            await callback.answer("FAQ not found.", show_alert=True)
            return
        
        text = format_faq_answer_message(faq['question'], faq['answer'])
        keyboard = get_faq_answer_keyboard(faq_id, page=page)
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
    except Exception as e:
        logger.error(f"FAQ view error: {e}")
        await callback.answer("Error showing answer.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "bot_stats")
async def callback_stats(callback: CallbackQuery):
    # This is a bit of a hack to reuse cmd_stats logic
    class DummyMessage:
        def __init__(self, message):
            self.message = message
        async def answer(self, text, parse_mode=None, reply_markup=None):
            await self.message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    await cmd_stats(DummyMessage(callback.message))
    await callback.answer()


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Help Guide</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "🔹 <b>/stats</b> — Total leads, status breakdown\n"
        "🔹 <b>/recent</b> — Last 5 latest leads with buttons\n"
        "🔹 <b>/search react</b> — 'react' keyword se search\n"
        "🔹 <b>/scrape</b> — Scraper manually trigger karo\n"
        "🔹 <b>/unnotified</b> — Abhi tak na bheje gaye leads\n"
        "\n"
        "<b>Button Actions:</b>\n"
        "🚀 Apply Now → Job URL open hota hai\n"
        "✅ Contacted → Status: Contacted ho jayega\n"
        "❌ Irrelevant → Lead reject ho jayegi\n"
        "🟣 Applied → Applied mark ho jayega\n"
        "↩️ Undo → Wapis unnotified kar do\n",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command('stats'))
async def cmd_stats(message: Message):
    # Gather stats using async wrappers
    total = await get_total_leads()
    status_counts = await get_leads_by_status()
    today_count = await get_today_leads_count()
    week_count = await get_week_leads_count()
    high_value = await get_high_value_count()

    stats = {
        'total': total,
        'unnotified': 0,
        'notified': 0,
        'contacted': 0,
        'applied': 0,
        'rejected': 0,
        'today': today_count,
        'this_week': week_count,
        'high_value': high_value,
    }
    for item in status_counts:
        stats[item['status']] = item['count']

    await message.answer(
        format_stats_message(stats),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command('recent'))
async def cmd_recent(message: Message):
    leads = await get_recent_leads(5)
    if not leads:
        await message.answer("📭 Koi lead abhi tak nahi mili.")
        return

    for lead in leads:
        text = format_lead_message(lead)
        keyboard = get_lead_keyboard(lead.id, lead.url)
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await asyncio.sleep(0.5)


@router.message(Command('unnotified'))
async def cmd_unnotified(message: Message):
    leads = await get_unnotified_leads(5)
    if not leads:
        await message.answer("✅ Sab leads notify ho chuki hain!")
        return

    total_count = await get_unnotified_count()
    await message.answer(
        f"🔵 <b>{total_count} Unnotified Leads</b> (showing first 5):",
        parse_mode=ParseMode.HTML,
    )

    for lead in leads:
        text = format_lead_message(lead)
        keyboard = get_lead_keyboard(lead.id, lead.url)
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await asyncio.sleep(0.5)


@router.message(Command('scrape'))
async def cmd_scrape(message: Message):
    await message.answer(
        "⏳ Scraper start ho raha hai... (Demo mode)\n"
        "Results kuch seconds mein aayenge.",
        parse_mode=ParseMode.HTML,
    )

    try:
        from leads.tasks import run_scraper_task
        result = run_scraper_task.delay('demo')
        await message.answer(
            f"🤖 Scraper task queued!\nTask ID: <code>{result.id}</code>\nNaye leads automatically alert honge.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.warning(f"Celery not available, running directly: {e}")
        await message.answer("⚠️ Celery not running. Running scraper directly...", parse_mode=ParseMode.HTML)
        try:
            from leads.scraper.base import DemoScraper
            from leads.tasks import _save_new_leads
            scraper = DemoScraper(headless=True)
            leads_data = await scraper.scrape()
            result = _save_new_leads(leads_data)  # This is sync, but fine for demo
            await message.answer(
                f"✅ Scraping complete!\n📋 Found: {result['total']}\n💾 New: {result['saved']}\n🔄 Duplicates: {result['duplicates']}",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e2:
            await message.answer(f"❌ Error: {e2}", parse_mode=ParseMode.HTML)


@router.message(Command('search'))
async def cmd_search(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /search <keyword>\nExample: /search react", parse_mode=ParseMode.HTML)
        return

    keyword = parts[1].strip()
    leads = await search_leads(keyword, 5)
    if not leads:
        await message.answer(f"🔍 '{keyword}' ke liye koi lead nahi mili.")
        return

    total = await get_search_total(keyword)
    await message.answer(
        f"🔍 <b>'{keyword}' ke liye {total} leads mili</b> (showing 5):",
        parse_mode=ParseMode.HTML,
    )

    for lead in leads:
        text = format_lead_message(lead)
        keyboard = get_lead_keyboard(lead.id, lead.url)
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await asyncio.sleep(0.5)

@router.message(Command('proposal'))
async def cmd_proposal(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📝 <b>Usage:</b> /proposal <job description>\nPaste the job text after the command.")
        return
    
    job_text = parts[1].strip()
    status_msg = await message.answer("🤖 <b>AI is generating your proposal...</b>", parse_mode=ParseMode.HTML)
    
    proposal = await generate_ai_proposal(job_text)
    
    await status_msg.edit_text(
        f"✅ <b>AI-Generated Proposal:</b>\n\n{proposal}",
        parse_mode=ParseMode.HTML
    )

@router.message(Command('coach'))
async def cmd_coach(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🤝 <b>AI Negotiation Coach</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Paste the client's message after the command to get strategic advice and a perfect reply.\n\n"
            "<b>Usage:</b> /coach [Client's Message]"
        )
        return
    
    client_msg = parts[1].strip()
    status_msg = await message.answer("🧠 <b>Analyzing client's psychology...</b>", parse_mode=ParseMode.HTML)
    
    advice = await generate_negotiation_advice(client_msg)
    
    await status_msg.edit_text(
        f"🤝 <b>Negotiation Strategy & Reply:</b>\n\n{advice}",
        parse_mode=ParseMode.HTML
    )


# ---------- CALLBACK HANDLERS ----------
@router.callback_query(F.data.startswith('contacted:'))
async def callback_contacted(callback: CallbackQuery):
    lead_id = int(callback.data.split(':')[1])
    try:
        lead = await get_lead_by_id(lead_id)
        await update_lead_status(lead, mark_method='mark_as_contacted')
        updated_text = format_lead_updated_message(lead, 'contacted')
        keyboard = get_status_updated_keyboard(lead.id, lead.url)
        await callback.message.edit_text(
            updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await callback.answer("✅ Marked as Contacted!")
    except ScrapedLead.DoesNotExist:
        await callback.answer("❌ Lead not found!", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith('reject:'))
async def callback_reject(callback: CallbackQuery):
    lead_id = int(callback.data.split(':')[1])
    try:
        lead = await get_lead_by_id(lead_id)
        await update_lead_status(lead, mark_method='mark_as_rejected')
        updated_text = format_lead_updated_message(lead, 'rejected')
        keyboard = get_status_updated_keyboard(lead.id, lead.url)
        await callback.message.edit_text(
            updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await callback.answer("❌ Marked as Irrelevant!")
    except ScrapedLead.DoesNotExist:
        await callback.answer("❌ Lead not found!", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith('applied:'))
async def callback_applied(callback: CallbackQuery):
    lead_id = int(callback.data.split(':')[1])
    try:
        lead = await get_lead_by_id(lead_id)
        await update_lead_status(lead, mark_method='mark_as_applied')
        updated_text = format_lead_updated_message(lead, 'applied')
        keyboard = get_status_updated_keyboard(lead.id, lead.url)
        await callback.message.edit_text(
            updated_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await callback.answer("🟣 Marked as Applied!")
    except ScrapedLead.DoesNotExist:
        await callback.answer("❌ Lead not found!", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith('ai_proposal:'))
async def callback_ai_proposal(callback: CallbackQuery):
    lead_id = int(callback.data.split(':')[1])
    try:
        lead = await get_lead_by_id(lead_id)
        # Combine title and description for better context
        job_content = f"Title: {lead.title}\nDescription: {lead.description}"
        
        await callback.answer("🤖 AI is vibing... generating proposal.")
        
        # Send a temporary status message
        status_msg = await callback.message.answer("⏳ <b>Generating your personalized AI proposal...</b>")
        
        proposal = await generate_ai_proposal(job_content)
        
        await status_msg.edit_text(
            f"✅ <b>AI-Generated Proposal for:</b> {lead.title}\n\n{proposal}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"AI Proposal callback error: {e}")
        await callback.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith('undo:'))
async def callback_undo(callback: CallbackQuery):
    lead_id = int(callback.data.split(':')[1])
    try:
        lead = await get_lead_by_id(lead_id)
        await update_lead_status(lead, status_field=ScrapedLead.Status.UNNOTIFIED)
        text = format_lead_message(lead)
        keyboard = get_lead_keyboard(lead.id, lead.url)
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.to_aiogram_markup(),
        )
        await callback.answer("↩️ Status reset to Unnotified!")
    except ScrapedLead.DoesNotExist:
        await callback.answer("❌ Lead not found!", show_alert=True)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data.startswith('note:'))
async def callback_note(callback: CallbackQuery):
    await callback.answer(
        "📝 Note feature coming soon!\nAbhi ke liye Django Admin mein notes add karein.",
        show_alert=True,
    )


# ---------- CONTACT FLOW (FSM) ----------

@router.callback_query(F.data == "agency_contact")
async def callback_contact_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ContactForm.waiting_for_name)
    await callback.message.edit_text(
        "📞 <b>Contact Us</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Please enter your <b>Full Name</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_status_updated_keyboard(0, "").to_aiogram_markup() # We just want the undo button to act as cancel? No, better use a custom back button
    )
    # Actually let's use a simpler way to cancel
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="back_to_main")]])
    await callback.message.edit_reply_markup(reply_markup=cancel_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("service:"))
async def callback_service_select(callback: CallbackQuery, state: FSMContext):
    service_map = {
        'web': 'Websites & Web Apps',
        'landing': 'Landing Pages',
        'software': 'Software Development',
        'ai': 'AI & Automation',
        'mobile': 'Mobile App Development',
        'bots': 'Bots & Automation',
        'speed': 'Speed Optimization',
        'hosting': 'Hosting & Deployment'
    }
    service_code = callback.data.split(':')[1]
    service_name = service_map.get(service_code, 'General')
    
    await state.update_data(service=service_name)
    await state.set_state(ContactForm.waiting_for_name)
    await callback.message.edit_text(
        f"✅ Interested in: <b>{service_name}</b>\n\n"
        "Please enter your <b>Full Name</b>:",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(ContactForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ContactForm.waiting_for_phone)
    await message.answer("Great! Now please enter your <b>Email or Phone Number</b>:")


@router.message(ContactForm.waiting_for_phone)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(ContactForm.waiting_for_message)
    await message.answer("Almost done! Please describe your <b>Project or Query</b>:")


@router.message(ContactForm.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    contact = data.get('contact')
    service = data.get('service', 'General Inquiry')
    user_msg = message.text
    
    # Save to database
    lead = await sync_to_async(AgencyLead.objects.create)(
        full_name=name,
        email=contact if '@' in contact else '',
        phone=contact if '@' not in contact else '',
        service_interested=service,
        message=user_msg,
        telegram_user_id=message.from_user.id
    )
    
    await state.clear()
    
    # Confirmation message
    await message.answer(
        "✅ <b>Thank you!</b> Your inquiry has been received.\n"
        "Our team will contact you shortly.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏠 Back to Main Menu: /start",
        parse_mode=ParseMode.HTML
    )
    
    # Notify Admin (optional, but good for "Real-time" feel)
    # We could send a message to settings.TELEGRAM_CHAT_ID here
    try:
        from config import settings
        admin_chat_id = settings.TELEGRAM_CHAT_ID
        if admin_chat_id:
            notification = (
                f"🚨 <b>New Agency Lead!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {name}\n"
                f"📞 <b>Contact:</b> {contact}\n"
                f"💎 <b>Service:</b> {service}\n"
                f"💬 <b>Message:</b> {user_msg}"
            )
            await message.bot.send_message(admin_chat_id, notification, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Admin notification failed: {e}")


# ---------- BOT STARTUP ----------
async def start_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or token == 'your-telegram-bot-token-from-botfather':
        logger.error(
            "❌ TELEGRAM_BOT_TOKEN not configured!\n"
            "   1. Go to @BotFather on Telegram\n"
            "   2. Create a new bot with /newbot\n"
            "   3. Copy the token to your .env file"
        )
        return

    # Use custom session for proxy/Cloudflare worker support
    api_base = getattr(settings, 'TELEGRAM_API_BASE_URL', 'https://api.telegram.org')
    if api_base and 'api.telegram.org' not in api_base:
        api = TelegramAPIServer.from_base(api_base)
        session = AiohttpSession(api=api)
    else:
        session = AiohttpSession()

    bot = Bot(token=token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Bot start karo"),
        BotCommand(command="stats", description="📊 Pipeline statistics"),
        BotCommand(command="recent", description="📋 Last 5 leads"),
        BotCommand(command="unnotified", description="🔵 Unnotified leads"),
        BotCommand(command="scrape", description="🤖 Scraper run karo"),
        BotCommand(command="search", description="🔍 Search leads"),
        BotCommand(command="proposal", description="📝 AI Proposal Generator"),
        BotCommand(command="coach", description="🤝 AI Negotiation Coach"),
        BotCommand(command="help", description="📖 Help guide"),
    ])

    logger.info("🤖 Israinsols Bot starting...")
    print("=" * 50)
    print("🤖 ISRAINSOLS TELEGRAM BOT IS RUNNING!")
    print("=" * 50)
    print(f"Bot token: {token[:10]}...{token[-5:]}")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    try:
        await dp.start_polling(bot, allowed_updates=['message', 'callback_query'])
    finally:
        await bot.session.close()


def run_bot():
    asyncio.run(start_bot())


if __name__ == '__main__':
    run_bot()