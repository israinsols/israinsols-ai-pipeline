from django.core.management.base import BaseCommand
from leads.discord_bot.bot import run_discord_bot

class Command(BaseCommand):
    help = 'Runs the Israinsols Discord Bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Israinsols Discord Bot...'))
        run_discord_bot()
