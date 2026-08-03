from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell import Cell

def get_users(config: dict) -> dict[tuple[str, str], list[str]]:
    """
    Returns:
    {
        (username, password): [
            "2023-2024",
            "2024-2025",
            ...
        ]
    }
    """
    
    file = Path(config["input"]["create_register_plan_sheet"])

    if not file.exists():
        return {}

    workbook = load_workbook(file, data_only=True)

    if "Sheet1" not in workbook.sheetnames:
        workbook.close()
        return {}

    sheet = workbook["Sheet1"]

    headers = [
        str(cell.value).strip() if cell.value else ""
        for cell in sheet[1]
    ]

    try:
        username_col = headers.index("LOGIN ID") + 1
        password_col = headers.index("PASSWORD") + 1
    except ValueError:
        workbook.close()
        return {}

    remarks_col = None
    for i, header in enumerate(headers, start=1):
        if header.lower() == "remarks":
            remarks_col = i
            break

    # Every non-fixed column after PASSWORD until Remarks is a Financial Year
    year_cols = []

    for col in range(password_col + 1, sheet.max_column + 1):
        if remarks_col and col >= remarks_col:
            break
        year_cols.append(col)

    result = {}

    for row in range(2, sheet.max_row + 1):

        if remarks_col:
            remarks = sheet.cell(row=row, column=remarks_col).value
            if str(remarks).strip().lower() == "done":
                continue

        username = sheet.cell(row=row, column=username_col).value
        password = sheet.cell(row=row, column=password_col).value

        if not username or not password:
            continue

        years = []

        for col in year_cols:
            value = sheet.cell(row=row, column=col).value
            if value:
                years.append(str(value).strip())

        result[
            (
                str(username).strip(),
                str(password).strip(),
            )
        ] = years

    workbook.close()
    return result


def mark_user_done(
    config: dict,
    username: str,
    password: str,
) -> bool:
    """
    Marks Remarks = Done for the matching username/password.

    Returns True if updated else False.
    """

    file = Path(config["input"]["users_sheet"])

    if not file.exists():
        return False

    workbook = load_workbook(file)

    if "Sheet1" not in workbook.sheetnames:
        workbook.close()
        return False

    sheet = workbook["Sheet1"]

    headers = [
        str(cell.value).strip() if cell.value else ""
        for cell in sheet[1]
    ]

    try:
        username_col = headers.index("LOGIN ID") + 1
        password_col = headers.index("PASSWORD") + 1
    except ValueError:
        workbook.close()
        return False

    remarks_col = None

    for i, header in enumerate(headers, start=1):
        if header.lower() == "remarks":
            remarks_col = i
            break

    if remarks_col is None:
        remarks_col = sheet.max_column + 1
        cell = sheet.cell(row=1, column=remarks_col) 
        assert isinstance(cell,Cell)
        cell.value = "Remarks"

    updated = False

    for row in range(2, sheet.max_row + 1):

        user = sheet.cell(row=row, column=username_col).value
        pwd = sheet.cell(row=row, column=password_col).value

        if (
            str(user).strip() == username
            and str(pwd).strip() == password
        ):
            cell = sheet.cell(row=1, column=remarks_col) 
            assert isinstance(cell,Cell)
            cell.value = "Done"
            updated = True
            break

    if updated:
        workbook.save(file)

    workbook.close()
    return updated