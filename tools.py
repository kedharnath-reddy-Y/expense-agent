import sqlite3
import datetime
from langchain.tools import tool

DB_FILE = "expenses.db"
CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Other"]


# ---------- tiny database helpers ----------
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
        """)


# ---------- tools the agent can call ----------
# The docstring and type hints are what the model reads to decide
# WHEN to call a tool and WHAT arguments to pass. Write them clearly.

@tool
def get_today() -> str:
    """Get today's date in YYYY-MM-DD format. Call this first whenever the user
    says things like 'today', 'yesterday', 'this week' or 'this month'."""
    return datetime.date.today().isoformat()


@tool
def add_expense(amount: float, category: str, description: str, expense_date: str) -> str:
    """Save a new expense. category must be one of: Food, Transport, Bills,
    Shopping, Other. expense_date must be YYYY-MM-DD."""
    if category not in CATEGORIES:
        return f"Invalid category. Choose from {CATEGORIES}"
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
            (amount, category, description, expense_date),
        )
    return f"Saved expense #{cur.lastrowid}: Rs.{amount} on {category} ({description}) on {expense_date}"


@tool
def list_expenses(start_date: str = "", end_date: str = "", category: str = "") -> str:
    """List expenses. All filters are optional. Dates are YYYY-MM-DD (inclusive).
    Use this to find an expense id or to answer questions like 'biggest expense'."""
    query, params = "SELECT * FROM expenses WHERE 1=1", []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if category:
        query += " AND category = ?"
        params.append(category)
    rows = db().execute(query + " ORDER BY date DESC, id DESC", params).fetchall()
    if not rows:
        return "No expenses found."
    return "\n".join(
        f"#{r['id']} | {r['date']} | Rs.{r['amount']} | {r['category']} | {r['description']}"
        for r in rows
    )


@tool
def get_summary(start_date: str, end_date: str) -> str:
    """Get total spending per category between two dates (YYYY-MM-DD, inclusive)."""
    rows = db().execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE date >= ? AND date <= ? GROUP BY category",
        (start_date, end_date),
    ).fetchall()
    if not rows:
        return "No expenses in that period."
    total = sum(r["total"] for r in rows)
    lines = [f"{r['category']}: Rs.{r['total']}" for r in rows]
    return "\n".join(lines) + f"\nTOTAL: Rs.{total}"


@tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense by its id. Use list_expenses first if you don't know the id."""
    with db() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return f"Deleted expense #{expense_id}" if cur.rowcount else f"No expense with id {expense_id}"


ALL_TOOLS = [get_today, add_expense, list_expenses, get_summary, delete_expense]
