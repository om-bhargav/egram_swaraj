import re

def is_bank_reconciliation_message(message: str) -> bool:
    pattern = (
        r"Bank Reconciliation of "
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r" month for the following account numbers "
        r"Bank-\{[\d,]+\}"
        r"(?: Post-\{[\d,]+\})?"
        r" should be freezed before close day book\."
    )

    return re.search(pattern, message) is not None

def is_daybook_closed_message(message: str) -> bool:
    pattern = (
        r"^Day book of "
        r"(0[1-9]|[12][0-9]|3[01])/"
        r"(0[1-9]|1[0-2])/"
        r"\d{4} "
        r"has been closed successfully$"
    )

    return bool(re.fullmatch(pattern, message))