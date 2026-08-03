from playwright.sync_api import TimeoutError
from .base_panel import BasePanel


class ReconsilationPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)

    def run(
        self,
        username: str,
        password: str,
        option: str,
    ):
        self.start_session()

        try:
            self.login(username, password)
            self.open_menu("Accounting Management")
            self.process_records(option)

        finally:
            self.close_session()

    def process_records(self, option: str):
        assert self.page

        option_map = {
            "bank": "B",
            "treasury": "T",
            "post_office": "P",
        }

        if option != "bank":
            return

        bank_idx = 1
        branch_idx = 1
        account_idx = 1

        while True:

            reconciliation_url = self.config["app"]["reconsilation_url"]

            if self.page.url != reconciliation_url:
                self.page.goto(
                    reconciliation_url,
                    wait_until="domcontentloaded",
                )

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                self.page.locator(
                    f"input[name='accountType'][value='{option_map[option]}']"
                ).check()

            bank = self.page.locator("#bankCodeId")
            bank_count = bank.locator("option").count()

            if bank_idx >= bank_count:
                break

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                bank.select_option(index=bank_idx)

            branch = self.page.locator("#bankBranchCode")
            branch_count = branch.locator("option").count()

            if branch_count <= 1:
                self.accept_bootboxes()

                bank_idx += 1
                branch_idx = 1
                account_idx = 1
                continue

            if branch_idx >= branch_count:
                bank_idx += 1
                branch_idx = 1
                account_idx = 1
                continue

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                branch.select_option(index=branch_idx)

            account = self.page.locator("#bankACNo")
            account_count = account.locator("option").count()

            if account_count <= 1:
                self.accept_bootboxes()

                branch_idx += 1
                account_idx = 1
                continue

            if account_idx >= account_count:
                branch_idx += 1
                account_idx = 1
                continue

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                account.select_option(index=account_idx)

            if self._month_book_not_closed():
                account_idx += 1
                continue

            self._process_current_combination()

            account_idx += 1

    def _process_current_combination(self):
        assert self.page

        print("Processing...")

        cash = self.page.locator(
            "input[name='cashBookBalance']"
        ).input_value()

        cash = str(
            int(
                float(
                    cash.replace(",", "")
                )
            )
        )

        self.page.locator(
            "input[name='closingBalance']"
        ).fill(cash)

        self.page.get_by_role(
            "button",
            name="Reconcile",
        ).click()

        self.accept_bootboxes()

        self.page.wait_for_load_state("networkidle")

        self.page.get_by_role(
            "button",
            name="Freeze",
        ).click()

        self.page.wait_for_load_state("networkidle")

        self.accept_bootboxes()

    def _month_book_not_closed(self) -> bool:
        assert self.page

        try:
            self.page.wait_for_url(
                lambda url: "home.htm" in url,
                timeout=1000,
            )

        except TimeoutError:
            return False

        try:
            modal = self.page.locator(
                ".bootbox.modal:visible"
            )

            modal.wait_for(
                state="visible",
                timeout=5000,
            )

            message = modal.locator(
                ".bootbox-body"
            ).inner_text().strip()

            if message.startswith(
                "Please close the Month Book"
            ):
                modal.locator(
                    "button.bootbox-accept"
                ).click()

                modal.wait_for(
                    state="hidden"
                )

                self.page.goto(
                    self.config["app"]["reconsilation_url"],
                    wait_until="networkidle",
                )

                return True

        except TimeoutError:
            pass

        return False