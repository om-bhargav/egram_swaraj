from .base_panel import BasePanel
from typing import List,Dict,Any
from data.plans import plans
from playwright.sync_api import expect,TimeoutError as PlaywrightTimeoutError
import time

TARGET_POPULATION_MAP = {
    "All": "#categoryAllId",
    "Women": "#categoryId0",
    "Children": "#categoryId1",
    "Youth": "#categoryId2",
    "Elderly": "#categoryId3",
    "OBC": "#categoryId4",
    "Person with disabilities": "#categoryId5",
}
 
MISSION_ANTYODAYA_MAP = {
    "None": "#lableid0",
    "Availability of drainage facilities": "#lableid1",
    "Community bio gas or recycle of waste": "#lableid2",
    "Community waste disposal system": "#lableid3",
    "Total no of households using clean energy (LPG/Bio gas)": "#lableid4",
}
class CreateAndRegisterPlanPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)

    # ---------------- Public ----------------
    def open_activity_pool_option(self, option_name: str):
        assert self.page

        # Open the Activity Pool dropdown if not already open
        dropdown = self.page.locator(
            "a.dropdown-toggle",
            has_text="Activity Pool"
        )

        dropdown.wait_for(state="visible")
        dropdown.click()

        # Wait for menu to appear
        option = self.page.locator(
            "ul.dropdown-menu[role='menu'] li a"
        ).filter(
            has_text=option_name
        )

        option.first.wait_for(state="visible")
        option.first.click()

        self.page.wait_for_load_state("networkidle")
    def run(
        self,
        username: str,
        password: str,
        years: List[str]
    ):
        self.start_session()

        try:
            self.login(username, password)
            self.process_years(years)
        finally:
            self.close_session()

    # ---------------- Navigation ----------------

    def open_create_plan(self):
        assert self.page

        self.open_menu("Panchayat Development Plan")
        self.open_activity_pool_option("Register Activity (Theme-wise)")

    # ---------------- Main Flow ----------------

    def process_years(
        self,
        years: list[str],
    ):
        assert self.page

        for year in years:
            print(f"Processing Financial Year: {year}")

            # Change financial year
            self.switch_unit(year)
            self.open_create_plan()
            # Create every plan for this year
            for plan in plans:
                self.fill_plan(plan,int(year.split("-")[0]))
                time.sleep(5)
                self.page.get_by_role(
                    "button",
                    name="Save and Forward",
                ).click()
                try:
                    self.accept_bootboxes()
                    self.open_create_plan()
                except Exception as e:
                        print(e)

    # ---------------- Actions ----------------
    def _fill_field(self, selector: str, value) -> None:
        """Fill a text/number input via locator.fill(); never keyboard typing."""
        assert self.page
        field = self.page.locator(selector)
        expect(field).to_be_visible()
        field.fill(str(value))
 
    def _check_if_unchecked(self, selector: str) -> None:
        """Check a checkbox/radio only if it isn't already checked."""
        assert self.page
        control = self.page.locator(selector)
        expect(control).to_be_visible()
        if not control.is_checked():
            control.check()
 
    def _check_mission_antyodaya_gap(self, label: str):
        assert self.page

        selector = MISSION_ANTYODAYA_MAP[label]

        # Open the multiselect
        self.page.locator("#maDivId .selectBox").click()

        # Wait until the list is expanded
        self.page.wait_for_function("""
            () => {
                const box = document.querySelector("#checkboxes");
                return box && box.style.display === "block";
            }
        """)

        # Click the label, not the hidden checkbox
        self.page.locator(selector).nth(0).click(force=True)
        self.page.wait_for_timeout(500)

    def _check_target_population(self, label: str) -> None:
        self._check_if_unchecked(TARGET_POPULATION_MAP[label])
 
    def _select_optional(self, selector: str, label, timeout: int = 5000) -> None:
        """
        Select a dropdown only if BOTH a value was supplied in the plan AND
        the dropdown has actually rendered (Major/Minor Head only appear
        for some activities).
        """
        assert self.page
        if not label:
            return
        dropdown = self.page.locator(selector)
        try:
            dropdown.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return
        self.select_when_ready(selector, label, timeout=timeout)
 
    def fill_plan(self, plan: dict, start_year: int) -> None:
        assert self.page
 
        # 1. Theme -> populates the Activity list
        self.select_when_ready("#themeId", plan["theme"])
 
        # 2. Activity -> populates Subject Area, Activity Type, Activity
        #    Nature, Mission Antyodaya, Major/Minor Head, and the Asset section
        self.select_when_ready("#themeActivityNameID", plan["activity"])
        # 3. Subject Area
        self.select_when_ready("#focusAreaId", plan["subject_area"])
        # 4. Activity Type
        self.select_when_ready("#activityTypeListId", plan["activity_type"]) 
        # 5. Activity Nature -> triggers another AJAX call
        self.select_when_ready("#workTypId", plan["activity_nature"]) 
        # 6. Description
        self._fill_field("#activityDescId", plan["description"]) 
        # 7. Mission Antyodaya (multiselect checkboxes)
        try:
            for gap in plan.get("mission_antyodaya_gaps", []):
                self._check_mission_antyodaya_gap(gap)
        except Exception as e:
            print(e) 
        # 8. Remarkable For
        self.select_when_ready("#activityFor", plan["remarkable_for"]) 
        # 9. Target Population (checkboxes)
        for population in plan.get("target_population", []):
            self._check_target_population(population) 
        # 10. Major Head (only if it rendered for this activity)
        self._select_optional("#submjrPrmptId", plan.get("major_head")) 
        # 11. Minor Head (only if it rendered for this activity)
        self._select_optional("#minorPrmptId", plan.get("minor_head")) 
        # 12. Funded by Panchayat (radio buttons -- ids are reversed in the
        #     underlying markup: "Yes" maps to the "...NoId" control)
        funded_by_panchayat = plan["funded_by_panchayat"]
        if funded_by_panchayat == "Yes":
            self._check_if_unchecked("#activityForCostlessFlagNoId")
        elif funded_by_panchayat == "No":
            self._check_if_unchecked("#activityForCostlessFlagYesId")
        else:
            raise ValueError(
                f"Unexpected value for funded_by_panchayat: {funded_by_panchayat!r}"
            ) 
        # 13. Estimated Completion (missing keys default to 0)
        estimated_completion = plan.get("estimated_completion", {})
        self._fill_field("#totDurYearId", estimated_completion.get("years", 0))
        self._fill_field("#totDurMonId", estimated_completion.get("months", 0))
        self._fill_field("#totDurDayId", estimated_completion.get("days", 0)) 
        # 14. Tentative Start -- year ALWAYS comes from the start_year
        #     argument, never from plan["tentative_start"]
        self.select_when_ready("#startYearId", str(start_year))
        self.select_when_ready("#startMonthId", plan["tentative_start"]["month"]) 
        # 15. Expected Beneficiaries (missing values default to 0)
        expected_beneficiaries = plan.get("expected_beneficiaries", {})
        self._fill_field("#expctdMenGenId", expected_beneficiaries.get("general", 0))
        self.page.evaluate("totalsumexpectedBeneficiaries()")
        self._fill_field("#expctdMenScId", expected_beneficiaries.get("sc", 0))
        self._fill_field("#expctdMenStId", expected_beneficiaries.get("st", 0))
        # 16. Estimated Total Cost
        self._fill_field("#totalCostId", plan["estimated_total_cost"]) 
        # 17. Asset Category -> populates Asset Sub Category
        self.select_when_ready("#maintAstCtgryId", plan["asset_category"]) 
        # 18. Asset Sub Category -> updates the (label-only) unit type
        self.select_when_ready("#mainAstSubCtgryId", plan["asset_sub_category"]) 
        # 19. Asset Unit Type is a label, not a field -- nothing to fill.
        # 20. Total Units
        self._fill_field("#mainAstNumOfUntId", plan["total_units"])
        # 21. Unit Cost
        self._fill_field("#mainAstUnitCostId", plan["unit_cost"]) 
    def submit(self):
        assert self.page

        self.page.get_by_role(
            "button",
            name="Save",
        ).click()

        self.accept_bootboxes()

        self.page.wait_for_load_state("networkidle")