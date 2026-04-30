import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.models import ScrapedLead

def inject():
    leads = [
        {
            "title": "Python Automation Expert Needed",
            "description": "We need a developer to automate our data entry tasks using Python and Selenium. Must have experience with web scraping.",
            "url": "https://www.freelancer.com/projects/python/Automation-Expert",
            "budget": "$50 - $100",
            "platform": "Freelancer.com"
        },
        {
            "title": "React Frontend Developer",
            "description": "Looking for a React developer to build a modern dashboard with glassmorphism UI.",
            "url": "https://www.freelancer.com/projects/react/Frontend-Dev",
            "budget": "$15/hr",
            "platform": "Freelancer.com"
        }
    ]
    
    for lead_data in leads:
        lead, created = ScrapedLead.objects.get_or_create(
            url=lead_data['url'],
            defaults=lead_data
        )
        if created:
            print(f"✅ Added: {lead.title}")
        else:
            print(f"ℹ️ Already exists: {lead.title}")

if __name__ == "__main__":
    inject()
