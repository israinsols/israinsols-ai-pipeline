"""
Israinsols Pipeline - Discord Bot Entry Point
"""
import logging
import discord
from discord.ext import commands
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('leads.discord')

class IsrainsolsDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Called when the bot is starting up."""
        from .handlers import LeadsCog, InteractionsCog
        
        # Add cogs
        await self.add_cog(LeadsCog(self))
        await self.add_cog(InteractionsCog(self))
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        print("=" * 50)
        print("🤖 ISRAINSOLS DISCORD BOT IS RUNNING!")
        print("=" * 50)

def run_discord_bot():
    token = settings.DISCORD_BOT_TOKEN
    if not token or token == 'your-discord-bot-token':
        logger.error("❌ DISCORD_BOT_TOKEN not configured in .env!")
        return

    bot = IsrainsolsDiscordBot()
    bot.run(token)

if __name__ == "__main__":
    run_discord_bot()
