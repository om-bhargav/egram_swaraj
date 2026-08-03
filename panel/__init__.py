from playwright.sync_api import TimeoutError
from .base_panel import BasePanel
from excel import update_records_status


class GPPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)

    def run(
        self,
        username: str,
        password: str,
        records: list[dict],
    ):
        self.start_session()

        try:
            self.login(username, password)

            lastFY = None

            for record in records:
                currFY = record.get("FY", "")

                if currFY != lastFY:
                    self.switch_unit(currFY)
                    self.open_panchayat_development_plan()
                    self.load_community_works()
                    lastFY = currFY

                record["isDone"] = self.process_record(record)

                if record["isDone"]:
                    self.load_community_works()

        finally:
            update_records_status(self.config, records)
            self.close_session()

    # ---------------- Navigation ----------------

    def open_panchayat_development_plan(self):
        assert self.page

        self.open_menu("Panchayat Development Plan")

        if not self.page.url.startswith(
            self.config["app"]["target_url"]
        ):
            self.page.goto(
                self.config["app"]["target_url"],
                wait_until="domcontentloaded",
            )

    # ---------------- Record Steps ----------------

    def load_community_works(self):
        assert self.page

        self.page.locator(
            "#activityTypeListId"
        ).select_option(label="Community Works")

        with self.page.expect_navigation(
            wait_until="domcontentloaded"
        ):
            self.page.locator("#saveId").click()

    def find_activity(self, activity_code: str):
        assert self.page

        search = self.page.locator(
            "#status_filter input[type='search']"
        )

        search.fill(str(activity_code))

        self.page.wait_for_load_state("networkidle")

        rows = self.page.locator("#status tbody tr")
        rows.first.wait_for()

        if rows.count() == 0:
            return None

        row = rows.first

        if "No matching records found" in row.inner_text():
            return None

        return row

    def process_record(self, record: dict) -> bool:
        assert self.page

        row = self.find_activity(record["AC"])

        if row is None:
            return False

        abandon_btn = row.locator("td").last.locator("a")

        classes = abandon_btn.get_attribute("class") or ""

        if "disabled" in classes or "not-active" in classes:
            return False

        if (
            not abandon_btn.is_visible()
            or not abandon_btn.is_enabled()
        ):
            return False

        abandon_btn.click()

        first_modal = self.page.locator(
            ".bootbox.modal:visible"
        ).filter(
            has_text="Are you going to abandon this activity?"
        )

        first_modal.wait_for(state="visible")

        first_modal.locator(
            "button.bootbox-accept"
        ).click()

        first_modal.wait_for(state="hidden")

        second_modal = self.page.locator(
            ".bootbox.modal:visible"
        ).filter(
            has_text="No further payment can be done"
        )

        second_modal.wait_for(state="visible")

        second_modal.locator(
            "button.bootbox-accept"
        ).click()

        second_modal.wait_for(state="hidden")

        self.page.wait_for_load_state("networkidle")

        try:
            success_modal = self.page.locator(
                ".bootbox.modal:visible"
            ).filter(
                has_text="Activity abondoned Successfully."
            )

            success_modal.wait_for(
                state="visible",
                timeout=3000,
            )

            success_modal.locator(
                "button.bootbox-accept"
            ).click()

            success_modal.wait_for(state="hidden")

        except TimeoutError:
            pass

        return True