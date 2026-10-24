import datetime
import pymysql
from pymysql.cursors import DictCursor
from langchain.tools import tool

CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Other"]


# ---------- database helpers ----------
def run(sql, params=()):
    """Open a connection, run one query, close it. Returns (rows, last_id, row_count)."""
    conn = pymysql.connect(
        host="localhost", user="root", password="",
        database="expenses_db", cursorclass=DictCursor, autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall(), cur.lastrowid, cur.rowcount
    finally:
        conn.close()


def init_db():
    run("""CREATE TABLE IF NOT EXISTS expenses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        amount DECIMAL(10,2) NOT NULL,
        category VARCHAR(50) NOT NULL,
        description VARCHAR(255),
        date DATE NOT NULL)""")


# ---------- tools ----------
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
    _, new_id, _ = run(
        "INSERT INTO expenses (amount, category, description, date) VALUES (%s, %s, %s, %s)",
        (amount, category, description, expense_date),
    )
    return f"Saved expense #{new_id}: Rs.{amount} on {category} ({description}) on {expense_date}"


@tool
def list_expenses(start_date: str = "", end_date: str = "", category: str = "") -> str:
    """List expenses. All filters are optional. Dates are YYYY-MM-DD (inclusive).
    Use this to find an expense id or to answer questions like 'biggest expense'."""
    query, params = "SELECT * FROM expenses WHERE 1=1", []
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)
    if category:
        query += " AND category = %s"
        params.append(category)
    rows, _, _ = run(query + " ORDER BY date DESC, id DESC", params)
    if not rows:
        return "No expenses found."
    return "\n".join(
        f"#{r['id']} | {r['date']} | Rs.{r['amount']} | {r['category']} | {r['description']}"
        for r in rows
    )


@tool
def get_summary(start_date: str, end_date: str) -> str:
    """Get total spending per category between two dates (YYYY-MM-DD, inclusive)."""
    rows, _, _ = run(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE date >= %s AND date <= %s GROUP BY category",
        (start_date, end_date),
    )
    if not rows:
        return "No expenses in that period."
    total = sum(r["total"] for r in rows)
    lines = [f"{r['category']}: Rs.{r['total']}" for r in rows]
    return "\n".join(lines) + f"\nTOTAL: Rs.{total}"


@tool
def delete_expense(expense_id: int) -> str:
    """Delete an expense by its id. Use list_expenses first if you don't know the id."""
    _, _, count = run("DELETE FROM expenses WHERE id = %s", (expense_id,))
    return f"Deleted expense #{expense_id}" if count else f"No expense with id {expense_id}"


ALL_TOOLS = [get_today, add_expense, list_expenses, get_summary, delete_expense]

