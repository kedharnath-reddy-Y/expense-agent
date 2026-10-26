import pymysql
from pymysql.cursors import DictCursor


# ---------- connection helper ----------
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
    run("""CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id VARCHAR(64) NOT NULL,
        role VARCHAR(10) NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX (thread_id))""")


# ---------- all the SQL lives here ----------
def add_expense(amount, category, description, expense_date):
    """Insert one expense and return its new id."""
    _, new_id, _ = run(
        "INSERT INTO expenses (amount, category, description, date) VALUES (%s, %s, %s, %s)",
        (amount, category, description, expense_date),
    )
    return new_id


def get_expenses(start_date="", end_date="", category="", limit=0):
    """Return a list of expense rows (dicts). All filters are optional."""
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
    query += " ORDER BY date DESC, id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    rows, _, _ = run(query, params)
    return rows


def get_totals(start_date, end_date):
    """Return one row per category: {'category': ..., 'total': ...}."""
    rows, _, _ = run(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE date >= %s AND date <= %s GROUP BY category",
        (start_date, end_date),
    )
    return rows


def delete_expense(expense_id):
    """Delete by id. Returns how many rows were deleted (0 or 1)."""
    _, _, count = run("DELETE FROM expenses WHERE id = %s", (expense_id,))
    return count


def update_expense(expense_id, amount=0, category="", description="", expense_date=""):
    """Change only the fields that were given. Returns how many rows changed."""
    fields, params = [], []
    if amount:
        fields.append("amount = %s")
        params.append(amount)
    if category:
        fields.append("category = %s")
        params.append(category)
    if description:
        fields.append("description = %s")
        params.append(description)
    if expense_date:
        fields.append("date = %s")
        params.append(expense_date)
    if not fields:
        return 0
    params.append(expense_id)
    _, _, count = run("UPDATE expenses SET " + ", ".join(fields) + " WHERE id = %s", params)
    return count


# ---------- saved chats ----------
def save_message(thread_id, role, text):
    """role is 'user' or 'assistant'."""
    run(
        "INSERT INTO messages (thread_id, role, text) VALUES (%s, %s, %s)",
        (thread_id, role, text),
    )


def get_messages(thread_id):
    """Return the saved chat for one browser, oldest first."""
    rows, _, _ = run(
        "SELECT role, text FROM messages WHERE thread_id = %s ORDER BY id",
        (thread_id,),
    )
    return rows


def get_chats():
    """One row per chat, newest first. The title is the first thing the user said."""
    rows, _, _ = run(
        "SELECT m.thread_id, MAX(m.id) AS last_id, "
        "(SELECT text FROM messages WHERE thread_id = m.thread_id AND role = 'user' ORDER BY id LIMIT 1) AS title "
        "FROM messages m GROUP BY m.thread_id ORDER BY last_id DESC"
    )
    return rows
