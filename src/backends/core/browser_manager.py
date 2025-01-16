import os
from typing import Optional
import traceback
from undetected_playwright.async_api import async_playwright, Playwright, Browser, Page


class BrowserManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not BrowserManager._initialized:
            self.playwright: Optional[Playwright] = None
            self.browser: Optional[Browser] = None
            self.page: Optional[Page] = None
            self.viewport_width: int = 0
            self.viewport_height: int = 0
            self.scroll_position: int = 0
            self.total_scroll_height: int = 0
            BrowserManager._initialized = True
            self._browser_ready = False

    async def initialize(self):
        """Initialize browser if not already initialized"""
        try:
            if not self.playwright:
                print("Initializing playwright...")
                self.playwright = await async_playwright().start()

            if not self._browser_ready:
                print("Launching browser...")
                chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
                # Generate a unique user data directory for each session
                user_data_dir = os.path.join(os.getenv("USERPROFILE"), "AppData", "Local", "Google", "Chrome",
                                             "User Data", "Default")
                print("User data directory:", user_data_dir)

                self.browser = await self.playwright.chromium.launch_persistent_context(
                    channel="chrome",
                    user_data_dir=user_data_dir,
                    executable_path=chrome_path,
                    headless=False,
                    no_viewport=True,
                    java_script_enabled=True,
                    bypass_csp=True,
                    is_mobile=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-infobars',
                        '--start-maximized',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                )
                self._browser_ready = True

            if not self.page or self.page.is_closed():
                print("Creating new page...")
                self.page = await self.browser.new_page()
                await self._setup_viewport()

        except Exception as e:
            print(f"Error during browser initialization: {str(e)}")
            print(traceback.format_exc())
            # await self.cleanup()
            self._browser_ready = False
            raise

    async def _setup_viewport(self):
        """Setup viewport dimensions"""
        print("Setting viewport...")
        screen_dimensions = await self.page.evaluate("""
            () => ({
                width: window.screen.availWidth,
                height: window.screen.availHeight
            })
        """)
        await self.page.set_viewport_size(screen_dimensions)

        await self.page.evaluate("""
            () => {
                window.moveTo(0, 0);
                window.resizeTo(screen.availWidth, screen.availHeight);
            }
        """)

        viewport_dimensions = await self.page.evaluate("""
            () => {
                return {
                    width: window.innerWidth || document.documentElement.clientWidth,
                    height: window.innerHeight || document.documentElement.clientHeight
                }
            }
        """)
        self.viewport_width = viewport_dimensions['width']
        self.viewport_height = viewport_dimensions['height']
        self.scroll_position = 0
        print(f"Viewport setup complete: {self.viewport_width}x{self.viewport_height}")

    async def navigate(self, url: str, timeout: int = 10000) -> bool:
        """Navigate to a URL in a new tab with proper error handling."""
        try:
            # Ensure the browser is initialized
            if not self.browser:
                await self.initialize()

            print(f"Navigating to: {url}")
            await self.page.goto(url)
            print("+++++++++++++++++++++++++++++++++++++")
            return True

        except Exception as e:
            print(f"Navigation error: {str(e)}")
            return False

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            self.page = None
            self.browser = None
            self.playwright = None
            self._browser_ready = False
            print("Browser cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    async def update_scroll_info(self):
        """Update scroll position and total height information"""
        if not self.page or self.page.is_closed():
            await self.initialize()

        try:
            scroll_info = await self.page.evaluate("""
                () => {
                    return {
                        scrollTop: window.pageYOffset || document.documentElement.scrollTop,
                        scrollHeight: Math.max(
                            document.body.scrollHeight,
                            document.documentElement.scrollHeight,
                            document.body.offsetHeight,
                            document.documentElement.offsetHeight
                        ),
                        viewportHeight: window.innerHeight
                    }
                }
            """)
            self.scroll_position = scroll_info["scrollTop"]
            self.total_scroll_height = scroll_info["scrollHeight"]
            return scroll_info
        except Exception as e:
            print(f"Error updating scroll info: {str(e)}")
            return None

    async def ensure_cursor_exists(self):
        """Ensure cursor element exists on the page"""
        if not self.page or self.page.is_closed():
            await self.initialize()

        try:
            cursor_exists = await self.page.evaluate("""
                () => {
                    let cursor = document.querySelector('.custom-cursor');
                    if (!cursor) {
                        cursor = document.createElement('div');
                        cursor.className = 'custom-cursor';
                        document.body.appendChild(cursor);
                        return false;
                    }
                    return true;
                }
            """)

            if not cursor_exists:
                await self.page.add_style_tag(content="""
                    .custom-cursor {
                        width: 20px;
                        height: 20px;
                        background: rgba(255, 0, 0, 0.5);
                        border: 2px solid red;
                        border-radius: 50%;
                        position: fixed;
                        pointer-events: none;
                        z-index: 99999;
                        transition: all 0.3s ease;
                        transform: translate(-50%, -50%);
                    }
                    .custom-cursor.clicking {
                        background: rgba(255, 0, 0, 0.8);
                        transform: translate(-50%, -50%) scale(0.8);
                    }
                """)
        except Exception as e:
            print(f"Error ensuring cursor exists: {str(e)}")

    def convert_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """Convert coordinates from squashed screenshot (900x600) to actual viewport dimensions"""
        scale_x = self.viewport_width / 1200
        scale_y = self.viewport_height / 800
        actual_x = int(x * scale_x)
        actual_y = int(y * scale_y)
        return actual_x, actual_y

    @property
    def is_initialized(self) -> bool:
        """Check if browser is properly initialized"""
        return bool(self.playwright and self.browser and self.page and not self.page.is_closed())
