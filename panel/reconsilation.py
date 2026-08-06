from playwright.sync_api import TimeoutError,expect,Page
from .base_panel import BasePanel
from helpers.reconsilation import is_bank_reconciliation_message,is_daybook_closed_message
from datetime import datetime,timedelta
import time
import traceback
import pymsgbox

class ReconsilationPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)
        self.username = None
        self.password = None

    def run(
        self,
        username: str,
        password: str,
    ):
        self.start_session()

        try:
            self.login(username, password)
            self.username = username
            self.password = password
            self.open_menu("Accounting Management")
            final_answer = self.close_day_books()
            return final_answer
        finally:
            self.close_session()
            
    def close_day_books(self):
        """
        Continuously closes day books until:
          1. Last Day Book Closed == Yesterday -> Stop
          2. Bank reconciliation popup appears -> Process reconciliation then continue
          3. Any other popup appears -> Wait 10 seconds and stop
        """
        assert self.page

        yesterday = (
            datetime.now() - timedelta(days=1)
        ).strftime("%d/%m/%Y")
        yesterday_date = datetime.strptime(
            yesterday,
            "%d/%m/%Y"
        ).date()
        last_date_closed = ""
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
            last_closed_date = datetime.strptime(
                last_closed,
                "%d/%m/%Y"
            ).date()
            # print(f"Last Closed : {last_closed}")
            # print(f"Yesterday   : {yesterday}")
            last_date_closed = last_closed
            # Finished
            if last_closed_date >= yesterday_date:
                print("Day Book already closed till yesterday.")
                return last_closed

            # Click Close Day Book
            self.page.get_by_role(
                "button",
                name="Close Day Book",
            ).click()
            time.sleep(10)
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
    
                self.process_reconsilation()
                
                continue
            
            # -------------------------------------------------------
            # Success
            # -------------------------------------------------------
            if is_daybook_closed_message(modal_text):
            
                print("Day book closed successfully.")
    
                self.accept_bootboxes()
    
                self.page.wait_for_timeout(1000)
    
                continue
            
            if self.maker_month_book_pending(modal_text):
               self._maker_login_process()
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
        return last_date_closed

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
            self.page.wait_for_load_state("networkidle")
            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                self.page.locator(
                    f"input[name='accountType'][value='B']"
                ).check()
            self.page.wait_for_load_state("networkidle")
            bank = self.page.locator("#bankCodeId")
            bank_count = bank.locator("option").count()

            if bank_idx >= bank_count:
                break

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                bank.select_option(index=bank_idx)
            self.page.wait_for_load_state("networkidle")
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
            self.page.wait_for_load_state("networkidle")
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

            self.page.wait_for_load_state("networkidle")
            isNotClosed = self._month_book_not_closed()
            if isNotClosed:
                account_idx += 1
                continue

            processed_now = self._process_current_combination()
            isProcessed = processed_now and isProcessed

            account_idx += 1
        return isProcessed

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
                account_idx += 1
                continue
            if self.no_accounts_available():
                break
            processed_now = self._process_current_combination()
            isProcessed = processed_now and isProcessed


            account_idx += 1
        return isProcessed
        
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
            
            self.page.wait_for_load_state("networkidle")
            if self.no_accounts_available():
                break

            if self._month_book_not_closed():
                account_idx += 1
                continue
            
            processed_now = self._process_current_combination()
            isProcessed = processed_now and isProcessed

            account_idx += 1
        return isProcessed

    def _process_current_combination(self) -> bool:
        print("Entered")
        assert isinstance(self.page, Page)

        try:
            print("Processing...")

            cash = self.page.locator(
                "input[name='cashBookBalance']"
            ).input_value()

            cash = str(
                    float(
                        cash.replace(",", "")
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

            self.page.locator("button:has-text('Freeze')").click()

            self.page.wait_for_load_state("networkidle")

            self.accept_bootboxes()

            return True

        except Exception as e:
            print(f"Error in _process_current_combination: {e}")
            traceback.print_exc()
            return False
        
    def _month_book_not_closed(self) -> bool:
        """
        After selecting an account, the page either:
          - settles on the reconciliation form (cashBookBalance becomes
            visible) -> month book IS closed, safe to process, return False
          - shows a "Please close the Month Book" popup -> return True
            (after accepting it)
 
        Polls directly for whichever of these actually appears on the page,
        instead of guessing from a URL snapshot within a fixed timeout.
        Account selection can route through more than one intermediate page,
        so a one-shot URL check can catch a transient URL either too early
        or too late and give the wrong answer depending on timing.
        """
        assert self.page
 
        cash_input = self.page.locator("input[name='cashBookBalance']").first
        modal = self.page.locator(".bootbox.modal:visible").first
 
        deadline_ms = 4000
        interval_ms = 200
        waited_ms = 0
 
        while waited_ms < deadline_ms:
            if cash_input.is_visible():
                return False
 
            if modal.is_visible():
                try:
                    message = modal.locator(
                        ".bootbox-body"
                    ).inner_text().strip()
                except Exception:
                    message = ""
 
                if message.startswith("Please close the Month Book"):
                    modal.locator(
                        "button.bootbox-accept"
                    ).click()
 
                    modal.wait_for(state="hidden")
 
                    return True
 
            self.page.wait_for_timeout(interval_ms)
            waited_ms += interval_ms
 
        return False
    
    def _maker_login_process(self) -> None:
        assert self.page

        # Close current admin session
        self.close_session()

        # Start a fresh browser/context
        self.start_session()

        # Login with Maker credentials
        self.login(
            self.config["mgr_user"]["username"],
            self.config["mgr_user"]["password"],
        )
        # self._close_scheme_day_books()
        self._mgr_process_dsc()
        # Close maker session
        self.close_session()

        # Start a fresh browser/context again
        self.start_session()

        # Login back with the admin credentials that were being processed
        assert self.username and self.password
        self.login(
            self.username,
            self.password,
        )
    def __open_close_day_books(self):
        assert self.page

        self.open_menu("Accounting Management")

        # Open Closing of Books menu
        self.page.get_by_role(
            "link",
            name="Closing of Books",
        ).click()

        # Wait for dropdown to become visible
        self.page.locator(
            "a[href='showSchemeWiseDayBook.htm']"
        ).wait_for(state="visible")

        # Click Schemewise Day Book Close
        with self.page.expect_navigation(
            wait_until="domcontentloaded",
        ):
            self.page.locator(
                "a[href='showSchemeWiseDayBook.htm']"
            ).click()

        self.page.wait_for_load_state("networkidle")

    def _mgr_process_dsc(self):
        assert self.page
        self.open_menu("DSC Management")

        # Click the dropdown menu to open it
        self.page.locator("li.dropdown > a.dropdown-toggle").click()

        # Get the menu items
        menu = self.page.locator(
            "li.dropdown.open ul.dropdown-menu li"
        )

        # Click the second last option
        with self.page.expect_navigation(
            wait_until="domcontentloaded",
        ):
            menu.nth(menu.count() - 2).locator("a").click()

        self.page.wait_for_load_state("networkidle")
        rows = self.page.locator("#dataTable tbody tr")
        row_count = rows.count()

        if row_count == 0:
            self.console.print(
                "[yellow]No month book files found for signing.[/yellow]"
            )
            return
        result = pymsgbox.confirm(
            text=(
                "Please start the DSC Generator software before proceeding.\n\n"
                "Once it is running, click 'Started'."
            ),
            title="DSC Generator Required",
            buttons=["Started", "Cancel"]
        )

        if result != "Started":
            return
        while True:
            rows = self.page.locator("#dataTable tbody tr")
            count = rows.count()

            if count == 0:
                self.console.print("[green]All month books signed.[/green]")
                break

            row = rows.first

            scheme = row.locator("td:nth-child(3)").inner_text().strip()
            self.console.print(f"[cyan]Signing Month Book: {scheme}[/cyan]")

            # Select radio
            row.locator("input[name='approveDsc']").check()

            # Click Apply Digital Signature
            row.locator("td:last-child a").click()

            # Wait until the signing modal is actually visible
            panel = self.page.locator("#panel")
            panel.wait_for(state="visible", timeout=60000)
            # Click Confirm Signing
            panel.locator("button.btn-success").click()

            def on_dialog(dialog):
                dialog.accept()

            self.page.on("dialog", on_dialog) 
            self.page.wait_for_load_state("networkidle")


    def _close_scheme_day_books(self) -> None:
        assert self.page
        
        self.__open_close_day_books()
        scheme = self.page.locator("#schemeid")

        schemes = [
            (
                scheme.locator("option").nth(i).get_attribute("value"),
                scheme.locator("option").nth(i).inner_text().strip(),
            )
            for i in range(1, scheme.locator("option").count())  # Skip ---Select---
        ]

        for value, name in schemes:
            # Re-locate after every reload
            scheme = self.page.locator("#schemeid")
            self.console.print(
                f"[cyan]Closing Day Book for: {name}[/cyan]"
            )

            with self.page.expect_navigation(
                wait_until="domcontentloaded"
            ):
                scheme.select_option(value=value)

            self.page.wait_for_load_state("networkidle")

            self.page.get_by_role(
                "button",
                name="Close Day Book",
            ).click()

            self.accept_bootboxes()

            self.page.wait_for_load_state("networkidle")

            self.console.print(
                f"[green]✓ Closed: {name}[/green]"
            )
            self.__open_close_day_books()