"""
Israinsols Pipeline - Stealth Browser Utilities (Phase 1)

Anti-detection techniques:
1. User-Agent rotation (har request pe alag UA)
2. Random delays (human-like browsing pattern)
3. Playwright stealth plugin (browser fingerprint mask)
4. Realistic viewport & locale settings
5. WebDriver property removal
"""
import asyncio
import random
import logging
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .user_agents import get_random_user_agent, get_random_viewport

logger = logging.getLogger('leads.scraper')


async def apply_stealth_scripts(page: Page):
    """
    Apply stealth JavaScript patches to hide bot indicators.
    Yeh scripts browser ke fingerprint ko mask karti hain
    taake website ko lagay ke real user hai.
    """
    await page.add_init_script("""
        // 1. Remove webdriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // 2. Realistic browser plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
            ]
        });

        // 3. Language settings
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

        // 4. Hardware fingerprints
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

        // 5. Chrome runtime (headless lacks this — PX checks it)
        if (!window.chrome) {
            window.chrome = {
                runtime: {
                    id: undefined,
                    onMessage: { addListener: () => {} },
                    sendMessage: () => {}
                },
                loadTimes: function() { return {}; },
                csi: function() { return {}; },
                app: { isInstalled: false }
            };
        }

        // 6. Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (params) => (
            params.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(params)
        );

        // 7. WebGL vendor — headless shows 'Google SwiftShader'
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };

        // 8. Network connection info
        Object.defineProperty(navigator, 'connection', {
            get: () => ({ effectiveType: '4g', rtt: 50, downlink: 10, saveData: false })
        });
    """)


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 5.0):
    """
    Human-like random delay between actions.
    Bot detection systems analyze timing patterns —
    constant delays look suspicious, random ones look human.
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting {delay:.1f}s (human-like delay)")
    await asyncio.sleep(delay)


async def human_like_scroll(page: Page):
    """
    Simulate human-like scrolling behavior.
    Real users don't jump to the bottom instantly.
    """
    viewport_height = page.viewport_size['height'] if page.viewport_size else 768

    # Scroll down in random chunks
    total_height = await page.evaluate("document.body.scrollHeight")
    current_position = 0

    while current_position < total_height:
        scroll_amount = random.randint(200, viewport_height)
        current_position += scroll_amount
        await page.evaluate(f"window.scrollTo(0, {current_position})")
        await asyncio.sleep(random.uniform(0.3, 1.2))

    # Scroll back up a bit (human behavior)
    await page.evaluate(f"window.scrollTo(0, {random.randint(0, 300)})")
    await asyncio.sleep(random.uniform(0.5, 1.0))


@asynccontextmanager
async def create_stealth_browser(
    headless: bool = True,
    proxy: Optional[str] = None,
):
    """
    Create a stealth Playwright browser context.

    Usage:
        async with create_stealth_browser() as (browser, context, page):
            await page.goto('https://example.com')
            content = await page.content()

    Args:
        headless: Run browser without GUI (True = invisible)
        proxy: Optional proxy URL (e.g., 'http://user:pass@proxy:8080')
    """
    playwright = await async_playwright().start()

    try:
        # Browser launch options
        launch_options = {
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--disable-extensions',
            ]
        }

        if proxy:
            launch_options['proxy'] = {'server': proxy}

        browser = await playwright.chromium.launch(**launch_options)

        # Random realistic settings
        ua = get_random_user_agent()
        viewport = get_random_viewport()

        context = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
        )

        # NOTE: Do NOT block resources — bot detectors (e.g. PerimeterX) flag
        # browsers that skip loading images/fonts, since real browsers load them.

        page = await context.new_page()

        # Apply stealth patches
        await apply_stealth_scripts(page)

        logger.info(f"Stealth browser created | UA: {ua[:50]}... | Viewport: {viewport}")

        yield browser, context, page

    finally:
        await playwright.stop()


async def safe_goto(page: Page, url: str, timeout: int = 30000) -> bool:
    """
    Safely navigate to a URL with error handling and retries.
    Returns True if successful, False otherwise.
    """
    for attempt in range(3):
        try:
            await random_delay(0.5, 2.0)
            response = await page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            if response and response.status == 200:
                logger.info(f"Successfully loaded: {url}")
                await random_delay(1.0, 3.0)  # Wait for dynamic content
                return True
            elif response:
                logger.warning(f"Got status {response.status} for {url}")
                if response.status == 403:
                    logger.error("Access forbidden — might be blocked!")
                    return False

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/3 failed for {url}: {e}")
            await random_delay(3.0, 8.0)  # Longer delay on failure

    logger.error(f"All attempts failed for {url}")
    return False
