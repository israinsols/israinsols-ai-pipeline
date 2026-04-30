import redis
from django.conf import settings
import os
import django

# Setup Django to get REDIS_URL from settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def fix():
    try:
        # Get Redis URL from settings
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        print(f"Connecting to Redis at {redis_url}...")
        
        r = redis.from_url(redis_url)
        
        # Set the config to stop the bgsave error
        r.config_set('stop-writes-on-bgsave-error', 'no')
        
        print("✅ Success! Redis is now unlocked and accepting writes.")
        print("You can now run 'python start_celery.py' without errors.")
        
    except Exception as e:
        print(f"❌ Failed to fix Redis: {e}")

if __name__ == "__main__":
    fix()
