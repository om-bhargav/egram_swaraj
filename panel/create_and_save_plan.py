from .base_panel import BasePanel
from typing import List
from data.plans import plans_for_current_year
from playwright.sync_api import expect,TimeoutError as PlaywrightTimeoutError
from datetime import datetime
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
class CreateAndSavePlanPanel(BasePanel):
    def __init__(self, config: dict):
        super().__init__(config)

    def run(
        self,
        username: str,
        password: str,
        years: List[str]
    ):
        self.start_session()

        try:
            self.login(username, password)
            self.allocate_funds()
            self.process_years(years)
            self.save_plans()
        finally:
            self.close_session()

    # ---------------- Navigation ----------------
    def allocate_funds(self):
        assert self.page
        self.open_menu("Funds / Resource Envelope")
        self.open_dropdown_option("Expected Funds Allocation","Expected Funds Allocation")
        self.page.wait_for_load_state("networkidle")
        # Fill 2,00,000
        self.page.locator("#avaBalGen15").fill("200000")
        # Click Save
        self.page.locator("#saveAsDraftId").click()
        # Wait for save request to complete
        self.page.wait_for_load_state("networkidle")
        self.accept_bootboxes()
        
    def open_create_plan(self):
        assert self.page

        self.open_menu("Panchayat Development Plan")
        self.open_dropdown_option("Activity Pool","Register Activity (Theme-wise)")

    # ---------------- Main Flow ----------------

    def process_years(
        self,
        years: list[str],
    ):
        assert self.page
        self.open_create_plan()
        # Create every plan for this year
        current_year = datetime.now().year
        for plan in plans_for_current_year:
            self.fill_plan(plan,current_year)
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
        operation_dropdown = self.page.locator("#operationTypeId")
        operation_dropdown.select_option(label=plan["operational_type"])

    def save_plans(self):
        assert self.page
        self.open_menu("Panchayat Development Plan")
        self.open_dropdown_option("Panchayat Development Plan","Register Plan")
        self.page.wait_for_load_state("networkidle")

        self.page.locator("#saveBtnId").click()


        self.page.wait_for_load_state("networkidle")
        self.accept_bootboxes()