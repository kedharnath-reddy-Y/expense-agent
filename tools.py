
import datetime

from langchain.tools import tool

import db  # All the SQL is in db.py


CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Other"]


# The docstring and type hints are what the model reads to decide
# WHEN to call a tool and WHAT arguments to pass. Write them clearly.


@tool
def get_today() -> str:
    """Get today's date in YYYY-MM-DD format. Call this first whenever the user
    says things like 'today', 'yesterday', 'this week' or 'this month'."""
    return datetime.date.today().isoformat()


@tool
def add_expense(
    amount: float,
    category: str,
    description: str,
    expense_date: str,
) -> str:
    """Save a new expense. category must be one of: Food, Transport, Bills,
    Shopping, Other. expense_date must be YYYY-MM-DD."""
    if category not in CATEGORIES:
        return f"Invalid category. Choose from {CATEGORIES}"

    new_id = db.add_expense(
        amount,
        category,
        description,
        expense_date,
    )

    return (
        f"Saved expense #{new_id}: Rs.{amount} on {category} "
        f"({description}) on {expense_date}"
    )


@tool
def list_expenses(
    start_date: str = "",
    end_date: str = "",
    category: str = "",
) -> str:
    """List expenses. All filters are optional. Dates are YYYY-MM-DD (inclusive).
    Use this to find an expense id or to answer questions like 'biggest expense'."""
    rows = db.get_expenses(start_date, end_date, category)

    if not rows:
        return "No expenses found."

    return "\n".join(
        f"#{r['id']} | {r['date']} | Rs.{r['amount']} | "
        f"{r['category']} | {r['description']}"
        for r in rows
    )


@tool
def get_summary(start_date: str, end_date: str) -> str:
    """Get total spending per category between two dates (YYYY-MM-DD, inclusive)."""
    rows = db.get_totals(start_date, end_date)

    if not rows:
        return "No expenses in that period."

    total = sum(r["total"] for r in rows)
    lines = [
        f"{r['category']}: Rs.{r['total']}"
        for r in rows
    ]

    return "\n".join(lines) + f"\nTOTAL: Rs.{total}"


@tool
def update_expense(
    expense_id: int,
    amount: float = 0,
    category: str = "",
    description: str = "",
    expense_date: str = "",
) -> str:
    """Change an existing expense. Only pass the fields that change and leave the
    others out. Use list_expenses first if you don't know the id."""
    if category and category not in CATEGORIES:
        return f"Invalid category. Choose from {CATEGORIES}"

    count = db.update_expense(
        expense_id,
        amount,
        category,
        description,
        expense_date,
    )

    if count:
        return f"Updated expense #{expense_id}"

    return (
        f"Nothing changed: no expense #{expense_id}, "
        "or the values were already the same"
    )


@tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense by its id. Use list_expenses first if you don't know the id."""
    count = db.delete_expense(expense_id)

    return (
        f"Deleted expense #{expense_id}"
        if count
        else f"No expense with id {expense_id}"
    )


ALL_TOOLS = [
    get_today,
    add_expense,
    list_expenses,
    get_summary,
    update_expense,
    delete_expense,
]
