# leads/management/commands/runbot.py
import asyncio
import logging
import sys
from pathlib import Path
from django.core.management.base import BaseCommand

# Ensure project root is in path (though Django usually handles it)
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

class Command(BaseCommand):
    help = 'Run the Telegram bot'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        self.stdout.write(self.style.SUCCESS('Starting bot...'))
        
        # Import the bot's main function
        from leads.bot.handlers import run_bot
        asyncio.run(run_bot())