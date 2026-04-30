"""
Israinsols Pipeline - Discord Views (Buttons)
Implements interactive buttons for Discord messages.
"""
import discord
from discord.ui import View, Button

class LeadView(View):
    """
    View for lead alerts.
    Replicates the Telegram lead keyboard.
    """
    def __init__(self, lead_id: int, job_url: str):
        super().__init__(timeout=None) # Persistent view
        self.lead_id = lead_id
        self.job_url = job_url

        # Apply Now Button (URL)
        self.add_item(Button(label="🚀 Apply Now", url=job_url, row=0))

        # Action Buttons
        self.add_item(Button(label="✅ Contacted", style=discord.ButtonStyle.success, custom_id=f"contacted:{lead_id}", row=1))
        self.add_item(Button(label="❌ Irrelevant", style=discord.ButtonStyle.danger, custom_id=f"reject:{lead_id}", row=1))
        
        # Extra Actions
        self.add_item(Button(label="🟣 Applied", style=discord.ButtonStyle.secondary, custom_id=f"applied:{lead_id}", row=2))
        self.add_item(Button(label="📝 Add Note", style=discord.ButtonStyle.secondary, custom_id=f"note:{lead_id}", row=2))

class StatusUpdatedView(View):
    """
    Simplified view after status update.
    """
    def __init__(self, lead_id: int, job_url: str):
        super().__init__(timeout=None)
        self.add_item(Button(label="🚀 Apply Now", url=job_url))
        self.add_item(Button(label="↩️ Undo", style=discord.ButtonStyle.secondary, custom_id=f"undo:{lead_id}"))

class AgencyMainView(View):
    """
    Main menu for the agency flow.
    """
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="💎 Our Services", style=discord.ButtonStyle.primary, custom_id="agency_services"))
        self.add_item(Button(label="❓ FAQs", style=discord.ButtonStyle.primary, custom_id="faq_list:0"))
        self.add_item(Button(label="📞 Contact Us", style=discord.ButtonStyle.success, custom_id="agency_contact"))
        self.add_item(Button(label="🚀 Pipeline Stats", style=discord.ButtonStyle.secondary, custom_id="bot_stats"))

class ServicesView(View):
    """
    Services menu.
    """
    def __init__(self):
        super().__init__(timeout=None)
        services = [
            ("🌐 Websites & Web Apps", "service:web"),
            ("🚀 Landing Pages", "service:landing"),
            ("💻 Software Development", "service:software"),
            ("🤖 AI & Automation", "service:ai"),
            ("📱 Mobile App Development", "service:mobile"),
            ("🤖 Bots & Automation", "service:bots"),
            ("⚡ Speed Optimization", "service:speed"),
            ("🛠 Code Review & Hosting", "service:hosting"),
        ]
        for label, custom_id in services:
            self.add_item(Button(label=label, style=discord.ButtonStyle.secondary, custom_id=custom_id))
        
        self.add_item(Button(label="⬅️ Back", style=discord.ButtonStyle.danger, custom_id="back_to_main"))

class FAQListView(View):
    """
    Paginated FAQ list.
    """
    def __init__(self, faqs: list, page: int = 0, page_size: int = 5):
        super().__init__(timeout=None)
        start = page * page_size
        end = start + page_size
        page_faqs = faqs[start:end]
        
        for faq in page_faqs:
            self.add_item(Button(label=faq['question'][:80], style=discord.ButtonStyle.secondary, custom_id=f"faq_view:{faq['id']}:{page}"))
        
        # Pagination
        if page > 0:
            self.add_item(Button(label="⬅️ Previous", style=discord.ButtonStyle.primary, custom_id=f"faq_list:{page-1}"))
        if end < len(faqs):
            self.add_item(Button(label="Next ➡️", style=discord.ButtonStyle.primary, custom_id=f"faq_list:{page+1}"))
            
        self.add_item(Button(label="🏠 Main Menu", style=discord.ButtonStyle.danger, custom_id="back_to_main"))

class FAQAnswerView(View):
    """
    View shown with an FAQ answer.
    """
    def __init__(self, faq_id: int, page: int = 0):
        super().__init__(timeout=None)
        self.add_item(Button(label="⬅️ Back to FAQs", style=discord.ButtonStyle.primary, custom_id=f"faq_list:{page}"))
        self.add_item(Button(label="📞 Contact Support", style=discord.ButtonStyle.success, custom_id="agency_contact"))
        self.add_item(Button(label="🏠 Main Menu", style=discord.ButtonStyle.danger, custom_id="back_to_main"))
