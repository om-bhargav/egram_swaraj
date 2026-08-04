from playwright.sync_api import Page, TimeoutError,expect
from browser import Browser

class BasePanel:
    def __init__(self, config: dict):
        self.browser = Browser(config)
        self.config = config
        self.page: Page | None = None

    # ---------------- Session ----------------

    def start_session(self):
        self.page = self.browser.start()

    def close_session(self):
        self.browser.close_context()
        self.page = None

    # ---------------- Login ----------------

    def login(self, username: str, password: str):
        assert self.page

        self.page.goto(
            self.config["app"]["base_urls"][0],
            wait_until="networkidle",
        )

        self.page.locator(
            "a[href='javascript:login()']"
        ).click()

        self.page.locator("#loginForm1").wait_for(
            state="visible"
        )

        self.page.locator("#username").fill(username)
        self.page.locator("#password").fill(password)

        print("Solve the CAPTCHA and click Login...")

        self.page.wait_for_url(
            lambda url: url.startswith(
                self.config["app"]["authenticated_url"]
            ),
            timeout=0,
        )

        self.close_pending_activities_popup()

    # ---------------- Common Popup ----------------

    def close_pending_activities_popup(self):
        assert self.page

        try:
            popup = self.page.locator("#myModalPopup")

            popup.wait_for(
                state="visible",
                timeout=3000,
            )

            popup.locator(
                "button.close"
            ).click()

            popup.wait_for(
                state="hidden",
                timeout=5000,
            )

        except TimeoutError:
            pass

    # ---------------- Navbar ----------------

    def open_menu(self, menu_name: str):
        assert self.page
    
        # Open the main menu
        self.page.locator("#navbarDropdown").click()
    
        # Wait for dashboard to appear
        dashboard = self.page.locator(".dashboard-grid")
        expect(dashboard).to_be_visible()
    
        # Find the requested menu by its visible text
        menu = dashboard.locator(
            "h5 a",
            has_text=menu_name,
        ).first
    
        expect(menu).to_be_visible()
    
        menu.click()
    
        self.page.wait_for_load_state("networkidle")
    # ---------------- Bootbox ----------------

    def accept_bootboxes(self):
        assert self.page

        while True:
            try:
                modal = self.page.locator(
                    ".bootbox.modal:visible"
                )

                modal.wait_for(
                    state="visible",
                    timeout=1500,
                )

                modal.locator(
                    "button.bootbox-accept"
                ).click()

                modal.wait_for(
                    state="hidden",
                    timeout=5000,
                )

            except TimeoutError:
                break


    def no_accounts_available(self) -> bool:
        assert self.page

        try:
            modal = self.page.locator(".bootbox.modal:visible")

            modal.wait_for(
                state="visible",
                timeout=1500,
            )

            message = (
                modal.locator(".bootbox-body")
                .inner_text()
                .strip()
            )

            if (
                message.startswith("No ")
                and message.endswith("Accounts available")
            ):
                modal.locator(
                    "button.bootbox-accept"
                ).click()

                modal.wait_for(
                    state="hidden",
                    timeout=5000,
                )

                return True

            return False

        except TimeoutError:
            return False
        
    def switch_unit(self, year: str):
        assert self.page

        self.page.goto(
            self.config["app"]["switch_unit_url"],
            wait_until="networkidle",
        )

        year_dropdown = self.page.locator("select#year")
        year_dropdown.wait_for(state="visible")
        year_dropdown.select_option(value=year)

        with self.page.expect_navigation(
            wait_until="domcontentloaded"
        ):
            self.page.locator("#switchunitsubmit").click()


    def select_when_ready(
        self,
        selector: str,
        label: str,
        timeout: int = 30000,
    ):
        """
        Wait until a dropdown is populated with the required option,
        then select it.
        """
        assert self.page

        dropdown = self.page.locator(selector)

        expect(dropdown).to_be_visible(timeout=timeout)

        self.page.wait_for_function(
            """
            ([selector, label]) => {
                const select = document.querySelector(selector);
                if (!select) return false;

                return [...select.options].some(
                    o => o.textContent.trim() === label.trim()
                );
            }
            """,
            arg=[selector, label],
            timeout=timeout,
        )

        dropdown.select_option(label=label)

        # Wait for any AJAX request triggered by onchange
        self.page.wait_for_load_state("networkidle")
