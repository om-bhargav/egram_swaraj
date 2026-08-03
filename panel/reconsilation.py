from playwright.sync_api import TimeoutError,expect
from .base_panel import BasePanel
from helpers.reconsilation import is_bank_reconciliation_message,is_daybook_closed_message
from datetime import datetime,timedelta
class ReconsilationPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)

    def run(
        self,
        username: str,
        password: str,
    ):
        self.start_session()

        try:
            self.login(username, password)
            self.open_menu("Accounting Management")
            final_answer = self.close_day_books()
            return final_answer
        finally:
            self.close_session()
            return False
            
    def close_day_books(self):
        """
        Continuously closes day books until:
          1. Last Day Book Closed == Yesterday -> Stop
          2. Bank reconciliation popup appears -> Process reconciliation then continue
          3. Any other popup appears -> Wait 10 seconds and stop
        """
        assert self.page
        target_url = self.config["app"]["close_day_book_url"]

        if self.page.url != target_url:
            self.page.goto(target_url)
            self.page.wait_for_load_state("networkidle")

        yesterday = (
            datetime.now() - timedelta(days=1)
        ).strftime("%d/%m/%Y")
        lst = []
        while True:
        
            # Open Close Day Book page
            self.open_close_day_book()
    
            # Wait until page loads
            expect(
                self.page.locator("form#bookOfAccountsForm")
            ).to_be_visible()
    
            # Read Last Day Book Closed
            last_closed = (
                self.page.locator(
                    "input[name='lastCloseDate']"
                )
                .input_value()
                .strip()
            )
    
            print(f"Last Closed : {last_closed}")
            print(f"Yesterday   : {yesterday}")
    
            # Finished
            if last_closed == yesterday:
                print("Day Book already closed till yesterday.")
                return
    
            # Click Close Day Book
            self.page.get_by_role(
                "button",
                name="Close Day Book",
            ).click()
    
            # Wait for popup
            self.page.wait_for_timeout(1500)
    
            modal = self.page.locator(".bootbox.modal.in")
    
            if modal.count() == 0:
                self.page.wait_for_timeout(1000)
                continue
            
            modal = self.page.locator(".bootbox.modal.in").last
            modal_text = modal.locator(".bootbox-body").inner_text().strip()
    
    
            # -------------------------------------------------------
            # Bank Reconciliation Required
            # -------------------------------------------------------
            if is_bank_reconciliation_message(modal_text):
            
                print("Bank reconciliation required.")
    
                self.accept_bootboxes()
    
                lst.append(self.process_reconsilation())
                
                continue
            
            # -------------------------------------------------------
            # Success
            # -------------------------------------------------------
            if is_daybook_closed_message(modal_text):
            
                print("Day book closed successfully.")
    
                self.accept_bootboxes()
    
                self.page.wait_for_timeout(1000)
    
                continue
            
            # -------------------------------------------------------
            # Unknown popup
            # -------------------------------------------------------
            print("Unknown popup detected.")
            print(modal_text)
    
            self.page.wait_for_timeout(10000)
    
            try:
                self.accept_bootboxes()
            except Exception:
                pass
            
            break
        return all(lst)

    def open_close_day_book(self):
        """
        Opens:
        Closing of Books -> Close Day Book
        """
        assert self.page

        # Open the dropdown
        menu = self.page.locator(
            "li.dropdown:has(a.dropdown-toggle:has-text('Closing of Books'))"
        )

        expect(menu).to_be_visible()

        menu.locator("a.dropdown-toggle").click()

        # Click Close Day Book
        option = menu.locator(
            "ul.dropdown-menu a",
            has_text="Close Day Book",
        )

        expect(option).to_be_visible()

        option.click()

        self.page.wait_for_load_state("networkidle")
    def process_reconsilation(self):
        """
        Process reconciliation for all account types.
    
        Bank:
            Bank -> Branch -> Account
    
        Treasury:
            Treasury Account
    
        Post Office:
            Post Office Account
        """
        areBanksProcessed = self._process_bank_accounts()
        areTresuryProcessed = self._process_treasury_accounts()
        arePostOfficeProcessed = self._process_post_office_accounts()
        return areBanksProcessed and areTresuryProcessed and arePostOfficeProcessed
    

    def _process_bank_accounts(self):
        assert self.page

        bank_idx = 1
        branch_idx = 1
        account_idx = 1
        isProcessed = True
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
                    f"input[name='accountType'][value='B']"
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
                isProcessed = False
                continue

            isProcessed = isProcessed and self._process_current_combination()

            account_idx += 1

    def _process_treasury_accounts(self):
        assert self.page

        account_idx = 1
        isProcessed = True
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
                    "input[name='accountType'][value='T']"
                ).check()

            account = self.page.locator("#treasuryACNo")
            account_count = account.locator("option").count()

            if account_idx >= account_count:
                break

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                account.select_option(index=account_idx)

            if self._month_book_not_closed():
                isProcessed = False
                account_idx += 1
                continue

            isProcessed = isProcessed and self._process_current_combination()

            account_idx += 1

    def _process_post_office_accounts(self):
        assert self.page

        account_idx = 1
        isProcessed = True
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
                    "input[name='accountType'][value='P']"
                ).check()

            account = self.page.locator("#poACNo")
            account_count = account.locator("option").count()

            if account_idx >= account_count:
                break

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                account.select_option(index=account_idx)

            if self._month_book_not_closed():
                isProcessed = False
                account_idx += 1
                continue

            isProcessed = isProcessed and self._process_current_combination()

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
        return True

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