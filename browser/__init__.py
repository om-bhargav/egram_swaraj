from playwright.sync_api import sync_playwright, Browser as PWBrowser, BrowserContext, Page


class Browser:
    def __init__(self, config: dict):
        self.config = config

        self.playwright = None
        self.browser: PWBrowser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def start(self) -> Page:
        if self.playwright is None:
            self.playwright = sync_playwright().start()

        if self.browser is None:
            self.browser = self.playwright.chromium.launch(
                channel="chrome",
                headless=False,
            )

        self.context = self.browser.new_context(
            accept_downloads=True,
            viewport={"width": 1400, "height": 900},
        )

        self.page = self.context.new_page()

        self.page.set_default_timeout(
            self.config["browser"]["timeout_ms"]
        )

        return self.page

    def goto(self, url: str):
        assert isinstance(self.page,Page)
        self.page.goto(
            url,
            wait_until="networkidle",
            timeout=self.config["browser"]["timeout_ms"],
        )

    def close_context(self):
        if self.context:
            self.context.close()
            self.context = None
            self.page = None

    def close(self):
        self.close_context()

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()