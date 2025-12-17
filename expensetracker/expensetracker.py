import sqlite3
from dataclasses import dataclass
from datetime import datetime
import csv
import os
import sys
from typing import Optional, List, Tuple

DB_FILE = "expenses.db"


def connect():
    return sqlite3.connect(DB_FILE)


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_cents INTEGER NOT NULL,
                category TEXT NOT NULL,
                note TEXT,
                date TEXT NOT NULL
            )
            """
        )
        conn.commit()


def parse_amount_to_cents(s: str) -> int:
    """
    Accepts inputs like: 12, 12.5, 12.50
    Returns integer cents.
    """
    s = s.strip().replace("$", "")
    if not s:
        raise ValueError("Empty amount.")
    # Use decimal-like parsing without importing Decimal (simple but safe enough here)
    if "." in s:
        dollars, cents = s.split(".", 1)
        cents = (cents + "00")[:2]
    else:
        dollars, cents = s, "00"
    if dollars.strip() == "":
        dollars = "0"
    if not (dollars.lstrip("-").isdigit() and cents.isdigit()):
        raise ValueError(f"Invalid amount: {s}")
    total = int(dollars) * 100 + (int(cents) if int(dollars) >= 0 else -int(cents))
    return total


def format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"


def normalize_date(date_str: str) -> str:
    """
    Accepts YYYY-MM-DD, or empty for today.
    Stores as YYYY-MM-DD.
    """
    date_str = date_str.strip()
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be YYYY-MM-DD (example: 2025-12-15).")


def add_expense(amount_cents: int, category: str, note: str, date: str):
    with connect() as conn:
        conn.execute(
            "INSERT INTO expenses (amount_cents, category, note, date) VALUES (?, ?, ?, ?)",
            (amount_cents, category.strip(), note.strip(), date),
        )
        conn.commit()


def list_expenses(category: Optional[str] = None, month: Optional[str] = None, limit: int = 50):
    """
    month: 'YYYY-MM' to filter
    """
    query = "SELECT id, amount_cents, category, note, date FROM expenses"
    params: List[str] = []
    where = []

    if category:
        where.append("category = ?")
        params.append(category.strip())

    if month:
        # match YYYY-MM%
        where.append("date LIKE ?")
        params.append(month.strip() + "%")

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(str(limit))

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        print("No expenses found.")
        return

    print("\nID | Date       | Amount   | Category        | Note")
    print("-" * 72)
    for eid, amount_cents, cat, note, date in rows:
        note_disp = (note or "").replace("\n", " ")
        if len(note_disp) > 28:
            note_disp = note_disp[:28] + "…"
        print(f"{eid:>2} | {date} | {format_cents(amount_cents):>8} | {cat:<14} | {note_disp}")
    print()


def summary_by_month(month: str):
    month = month.strip()
    if len(month) != 7:
        raise ValueError("Month must be YYYY-MM (example: 2025-12).")

    with connect() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM expenses WHERE date LIKE ?",
            (month + "%",),
        ).fetchone()[0]
        cats = conn.execute(
            """
            SELECT category, COALESCE(SUM(amount_cents), 0) as s
            FROM expenses
            WHERE date LIKE ?
            GROUP BY category
            ORDER BY s DESC
            """,
            (month + "%",),
        ).fetchall()

    print(f"\nSummary for {month}")
    print("-" * 30)
    print(f"Total: {format_cents(total)}\n")
    if cats:
        print("By category:")
        for cat, s in cats:
            print(f"  - {cat}: {format_cents(s)}")
    else:
        print("No expenses recorded for that month.")
    print()


def delete_expense(expense_id: int):
    with connect() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        if cur.rowcount == 0:
            print("No expense with that ID.")
        else:
            print("Deleted.")


def export_csv(filepath: str):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, date, amount_cents, category, note FROM expenses ORDER BY date ASC, id ASC"
        ).fetchall()

    if not rows:
        print("Nothing to export.")
        return

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "amount", "category", "note"])
        for eid, date, amount_cents, category, note in rows:
            writer.writerow([eid, date, format_cents(amount_cents), category, note or ""])

    print(f"Exported {len(rows)} rows to {filepath}")


def menu():
    print("\n=== Expense Tracker ===")
    print("1) Add expense")
    print("2) List expenses")
    print("3) Summary (by month)")
    print("4) Delete expense")
    print("5) Export CSV")
    print("0) Quit")


def main():
    init_db()

    while True:
        menu()
        choice = input("Choose: ").strip()

        try:
            if choice == "1":
                amount = input("Amount (e.g. 12.50): ")
                amount_cents = parse_amount_to_cents(amount)
                category = input("Category (e.g. food, transport): ").strip() or "uncategorized"
                note = input("Note (optional): ")
                date = normalize_date(input("Date YYYY-MM-DD (blank = today): "))
                add_expense(amount_cents, category, note, date)
                print("Added.")

            elif choice == "2":
                cat = input("Filter category (blank = none): ").strip() or None
                month = input("Filter month YYYY-MM (blank = none): ").strip() or None
                limit_str = input("Limit (default 50): ").strip()
                limit = int(limit_str) if limit_str else 50
                list_expenses(category=cat, month=month, limit=limit)

            elif choice == "3":
                month = input("Month YYYY-MM: ")
                summary_by_month(month)

            elif choice == "4":
                eid = int(input("Expense ID to delete: "))
                delete_expense(eid)

            elif choice == "5":
                path = input("CSV file path (default expenses_export.csv): ").strip() or "expenses_export.csv"
                export_csv(path)

            elif choice == "0":
                print("Bye!")
                return
            else:
                print("Invalid choice.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
