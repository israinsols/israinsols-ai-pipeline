"""
Israinsols Pipeline - Discord Handlers & Commands
Implements logic for slash commands and button interactions.
"""
import logging
import discord
from discord import app_commands, Interaction, TextStyle
from discord.ext import commands
from django.utils import timezone
from django.db.models import Count, Q
from asgiref.sync import sync_to_async

from leads.models import ScrapedLead, FAQ, AgencyLead
from .formatters import (
    format_lead_message_discord, format_stats_message_discord,
    format_agency_welcome_discord, format_faq_answer_discord
)
from .views import (
    LeadView, StatusUpdatedView, AgencyMainView, 
    ServicesView, FAQListView, FAQAnswerView
)

logger = logging.getLogger('leads.discord')

# ---------- Modal for Contact Form ----------
class ContactModal(discord.ui.Modal, title='Contact Israinsols'):
    full_name = discord.ui.TextInput(label='Full Name', placeholder='Your name...', required=True)
    contact_info = discord.ui.TextInput(label='Email or Phone', placeholder='How can we reach you?', required=True)
    message = discord.ui.TextInput(label='Project Details', style=TextStyle.long, placeholder='Tell us about your project...', required=True)

    def __init__(self, service='General Inquiry'):
        super().__init__()
        self.service = service

    async def on_submit(self, interaction: Interaction):
        # Save to database
        await sync_to_async(AgencyLead.objects.create)(
            full_name=self.full_name.value,
            email=self.contact_info.value if '@' in self.contact_info.value else '',
            phone=self.contact_info.value if '@' not in self.contact_info.value else '',
            service_interested=self.service,
            message=self.message.value,
            telegram_user_id=None # We could add a discord_user_id field to model later
        )
        
        await interaction.response.send_message(
            "✅ **Thank you!** Your inquiry has been received.\nOur team will contact you shortly.",
            ephemeral=True
        )
        
        # Notify Admin Channel (if configured)
        from django.conf import settings
        admin_channel_id = settings.DISCORD_CHANNEL_ID
        if admin_channel_id:
            try:
                channel = interaction.client.get_channel(int(admin_channel_id))
                if channel:
                    embed = discord.Embed(title="🚨 New Agency Lead!", color=discord.Color.blue())
                    embed.add_field(name="👤 Name", value=self.full_name.value)
                    embed.add_field(name="📞 Contact", value=self.contact_info.value)
                    embed.add_field(name="💎 Service", value=self.service)
                    embed.add_field(name="💬 Message", value=self.message.value, inline=False)
                    await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Discord admin notification failed: {e}")

# ---------- Cog for Lead Commands ----------
class LeadsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="📊 Show pipeline statistics")
    async def stats(self, interaction: Interaction):
        # Gather stats
        total = await sync_to_async(ScrapedLead.objects.count)()
        status_counts = await sync_to_async(lambda: list(ScrapedLead.objects.values('status').annotate(count=Count('id'))))()
        
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = await sync_to_async(ScrapedLead.objects.filter(scraped_at__gte=today_start).count)()
        
        # Format and send
        stats_data = {'total': total, 'today': today_count}
        for item in status_counts:
            stats_data[item['status']] = item['count']
            
        message = format_stats_message_discord(stats_data)
        await interaction.response.send_message(message)

    @app_commands.command(name="recent", description="📋 Show latest 5 leads")
    async def recent(self, interaction: Interaction):
        leads = await sync_to_async(lambda: list(ScrapedLead.objects.all()[:5]))()
        if not leads:
            await interaction.response.send_message("📭 No leads found.", ephemeral=True)
            return

        await interaction.response.send_message("📋 **Latest Leads:**", ephemeral=True)
        for lead in leads:
            text = format_lead_message_discord(lead)
            view = LeadView(lead.id, lead.url)
            await interaction.channel.send(text, view=view)

    @app_commands.command(name="scrape", description="🤖 Trigger scraper manually (Demo mode)")
    async def scrape(self, interaction: Interaction):
        await interaction.response.send_message("⏳ Scraper started... Results will appear soon.", ephemeral=True)
        try:
            from leads.tasks import run_scraper_task
            run_scraper_task.delay('demo')
        except Exception as e:
            logger.error(f"Discord scrape command error: {e}")
            await interaction.followup.send(f"❌ Error triggering scraper: {e}", ephemeral=True)

# ---------- Cog for Interaction Handling ----------
class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get('custom_id', '')
        
        # --- Lead Actions ---
        if ':' in custom_id:
            action, lead_id_str = custom_id.split(':', 1)
            if action in ['contacted', 'reject', 'applied', 'undo', 'faq_view', 'service']:
                await self.handle_action(interaction, action, lead_id_str)
                return

        # --- Simple Button Actions ---
        if custom_id == "agency_services":
            await interaction.response.edit_message(content="💎 **Our Core Services**", view=ServicesView())
        elif custom_id == "agency_contact":
            await interaction.response.send_modal(ContactModal())
        elif custom_id == "back_to_main":
            await interaction.response.edit_message(content=format_agency_welcome_discord(), view=AgencyMainView())
        elif custom_id == "bot_stats":
            # Re-use stats logic or send embed
            await interaction.response.send_message("📊 Use `/stats` for full statistics.", ephemeral=True)

    async def handle_action(self, interaction, action, data_str):
        if action == 'service':
            # Start contact modal with pre-selected service
            service_map = {'web': 'Websites', 'landing': 'Landing Pages', 'software': 'Software', 'ai': 'AI', 'mobile': 'Mobile', 'bots': 'Bots', 'speed': 'Speed', 'hosting': 'Hosting'}
            await interaction.response.send_modal(ContactModal(service=service_map.get(data_str, 'General')))
            return

        if action == 'faq_list':
            page = int(data_str)
            faqs = await sync_to_async(lambda: list(FAQ.objects.filter(is_active=True).values('id', 'question', 'answer')))()
            await interaction.response.edit_message(content="❓ **Frequently Asked Questions**", view=FAQListView(faqs, page=page))
            return

        if action == 'faq_view':
            faq_id, page = map(int, data_str.split(':'))
            faq = await sync_to_async(FAQ.objects.get)(id=faq_id)
            await interaction.response.edit_message(content=format_faq_answer_discord(faq.question, faq.answer), view=FAQAnswerView(faq_id, page))
            return

        # Lead status updates
        try:
            lead_id = int(data_str)
            lead = await sync_to_async(ScrapedLead.objects.get)(id=lead_id)
            
            if action == 'contacted':
                await sync_to_async(lead.mark_as_contacted)()
                await interaction.response.edit_message(content=f"✅ **Lead Updated!**\n📊 Status: **CONTACTED**", view=StatusUpdatedView(lead.id, lead.url))
            elif action == 'reject':
                await sync_to_async(lead.mark_as_rejected)()
                await interaction.response.edit_message(content=f"❌ **Lead Updated!**\n📊 Status: **REJECTED**", view=StatusUpdatedView(lead.id, lead.url))
            elif action == 'applied':
                await sync_to_async(lead.mark_as_applied)()
                await interaction.response.edit_message(content=f"🟣 **Lead Updated!**\n📊 Status: **APPLIED**", view=StatusUpdatedView(lead.id, lead.url))
            elif action == 'undo':
                lead.status = 'unnotified'
                await sync_to_async(lead.save)(update_fields=['status', 'updated_at'])
                await interaction.response.edit_message(content=format_lead_message_discord(lead), view=LeadView(lead.id, lead.url))
            
            await interaction.followup.send(f"Status updated for Lead #{lead_id}", ephemeral=True)
        except Exception as e:
            logger.error(f"Discord interaction error: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
