from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.cell import Cell

def get_reconciliation_users(config: dict) -> dict[tuple[str, str], str]:
    """
    Returns:
    {
        (username, password): "bank" | "treasury" | "post_office"
    }
    """

    workbook = load_workbook(
        Path(config["input"]["reconsilation_sheet"]),
        data_only=True,
    )

    records_sheet = workbook["Sheet1"]
    users_sheet = workbook["useridpass"]

    # GP -> (username, password)
    credentials = {}

    for row in users_sheet.iter_rows(min_row=2, values_only=True):
        gp, username, password = row[:3]

        if not gp or not username or not password:
            continue

        credentials[str(gp).strip().upper()] = (
            str(username).strip(),
            str(password).strip(),
        )

    result = {}

    for row in records_sheet.iter_rows(min_row=2, values_only=True):
        (
            block,
            gp,
            daybook,
            month_date,
            reconciliation,
            bank,
            treasury,
            post_office,
            remarks,
        ) = row[:9]

        if not gp:
            continue

        if str(reconciliation).strip().lower() != "yes":
            continue

        # Skip already processed records
        if str(remarks).strip().lower() == "done":
            continue

        gp = str(gp).strip().upper()

        if gp not in credentials:
            continue

        option = None

        if str(bank).strip().lower() == "yes":
            option = "bank"
        elif str(treasury).strip().lower() == "yes":
            option = "treasury"
        elif str(post_office).strip().lower() == "yes":
            option = "post_office"

        if option is None:
            continue

        result[credentials[gp]] = option

    return result


def update_reconciliation_remarks(
    config: dict,
    users: list[tuple[str, str]],
) -> bool:
    """
    Marks Remarks = 'Done' for the given (username, password) pairs.

    Returns:
        True  -> workbook updated successfully
        False -> file/sheet/config error
    """

    try:
        workbook_path = Path(config["input"]["reconsilation_sheet"])
    except KeyError:
        return False

    if not workbook_path.exists():
        return False

    try:
        workbook = load_workbook(workbook_path)
    except (FileNotFoundError, InvalidFileException):
        return False

    try:
        if "Sheet1" not in workbook.sheetnames:
            return False

        if "useridpass" not in workbook.sheetnames:
            return False

        records_sheet = workbook["Sheet1"]
        users_sheet = workbook["useridpass"]

        # (username, password) -> GP
        credentials: dict[tuple[str, str], str] = {}

        for row in users_sheet.iter_rows(min_row=2, values_only=True):
            if len(row) < 3:
                continue

            gp, username, password = row[:3]

            if not gp or not username or not password:
                continue

            credentials[
                (
                    str(username).strip(),
                    str(password).strip(),
                )
            ] = str(gp).strip().upper()

        target_gps = {
            credentials[user]
            for user in users
            if user in credentials
        }

        if not target_gps:
            return True

        updated = False

        for row in records_sheet.iter_rows(min_row=2):
            gp = row[1].value

            if not gp:
                continue

            if str(gp).strip().upper() in target_gps:
                assert isinstance(row[8],Cell)
                row[8].value = "Done"  # Remarks column
                updated = True

        if updated:
            workbook.save(workbook_path)

        return True

    finally:
        workbook.close()