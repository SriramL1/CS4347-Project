# operations.py - CS-4347 Milestone 2 (100% COMPLETE - All Functions Implemented)
import sqlite3
from datetime import datetime, timedelta
from database import create_connection

def search_books(query: str):
    """
    EXACTLY matches PDF example:
    - Case-insensitive substring search on ISBN, Title, or any Author name
    - Returns all matching books with comma-separated authors
    - Correct IN/OUT availability
    search("will") → 4 books as shown in PDF
    """
    conn = create_connection()
    c = conn.cursor()

    pattern = f"%{query.strip()}%"

    sql = """
    SELECT 
        b.Isbn,
        b.Title,
        GROUP_CONCAT(a.Name, ', ') AS authors,
        CASE 
            WHEN EXISTS(SELECT 1 FROM BOOK_LOANS bl 
                        WHERE bl.Isbn = b.Isbn AND bl.Date_in IS NULL) 
            THEN 'OUT' 
            ELSE 'IN' 
        END AS availability
    FROM BOOK b
    LEFT JOIN BOOK_AUTHORS ba ON b.Isbn = ba.Isbn
    LEFT JOIN AUTHORS a ON ba.Author_id = a.Author_id
    WHERE LOWER(b.Isbn) LIKE LOWER(?)
       OR LOWER(b.Title) LIKE LOWER(?)
       OR LOWER(a.Name) LIKE LOWER(?)
    GROUP BY b.Isbn
    ORDER BY b.Isbn
    """

    c.execute(sql, (pattern, pattern, pattern))
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        authors = row[2] if row[2] else "Unknown"
        results.append({
            "isbn": row[0],
            "title": row[1],
            "authors": authors,
            "availability": row[3]
        })
    return results


def checkout_book(isbn: str, card_id: str) -> str:
    """
    Checkout requirements:
    - Validate book & borrower exist
    - Max 3 active loans per borrower
    - Book not already checked out
    - Due date = today + 14 days
    """
    conn = create_connection()
    c = conn.cursor()

    # Validate book
    c.execute("SELECT Title FROM BOOK WHERE Isbn = ?", (isbn,))
    if not c.fetchone():
        conn.close()
        return "Error: Book does not exist"

    # Validate borrower
    c.execute("SELECT Bname FROM BORROWER WHERE Card_id = ?", (card_id,))
    if not c.fetchone():
        conn.close()
        return "Error: Invalid Card ID"

    # Max 3 active loans
    c.execute("SELECT COUNT(*) FROM BOOK_LOANS WHERE Card_id = ? AND Date_in IS NULL", (card_id,))
    if c.fetchone()[0] >= 3:
        conn.close()
        return "Error: Borrower already has 3 books checked out"

    # Already checked out?
    c.execute("SELECT 1 FROM BOOK_LOANS WHERE Isbn = ? AND Date_in IS NULL", (isbn,))
    if c.fetchone():
        conn.close()
        return "Error: Book already checked out"

    # Insert loan
    today = datetime.now().date()
    due = today + timedelta(days=14)
    c.execute("INSERT INTO BOOK_LOANS (Isbn, Card_id, Date_out, Due_date) VALUES (?, ?, ?, ?)",
              (isbn, card_id, today, due))
    conn.commit()
    conn.close()
    return f"Success: Book checked out to {card_id}. Due: {due}"


def checkin_book(isbn: str, card_id: str) -> str:
    """
    Checkin requirements:
    - Update Date_in to today
    - Refresh fines after checkin
    """
    conn = create_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE BOOK_LOANS 
        SET Date_in = date('now') 
        WHERE Isbn = ? AND Card_id = ? AND Date_in IS NULL
    """, (isbn, card_id))

    if c.rowcount == 0:
        conn.close()
        return "Error: No active loan found for this book and card"

    conn.commit()
    refresh_fines()
    conn.close()
    return "Success: Book checked in"


def add_borrower(ssn: str, bname: str, address: str, phone: str = None) -> str:
    """
    Add borrower requirements:
    - SSN unique
    - Auto-generate Card_id (ID000001, ID000002...)
    - Required: SSN, Name, Address, Phone
    """
    conn = create_connection()
    c = conn.cursor()

    # Check SSN unique
    c.execute("SELECT 1 FROM BORROWER WHERE Ssn = ?", (ssn,))
    if c.fetchone():
        conn.close()
        return "Error: SSN already exists"

    # Generate next Card_id
    c.execute("SELECT MAX(CAST(SUBSTR(Card_id, 3) AS INTEGER)) FROM BORROWER")
    max_num = c.fetchone()[0]
    next_num = (max_num or 0) + 1
    card_id = f"ID{next_num:06d}"

    # Insert
    c.execute("INSERT INTO BORROWER (Card_id, Ssn, Bname, Address, Phone) VALUES (?, ?, ?, ?, ?)",
              (card_id, ssn, bname, address, phone))
    conn.commit()
    conn.close()
    return f"Success: Borrower added with Card ID {card_id}"


def refresh_fines():
    """
    Fine requirements:
    - $0.25 per day late (after Due_date)
    - For active loans (Date_in NULL) use today
    - For checked-in loans use Date_in
    - Update/insert Fine_amt
    """
    conn = create_connection()
    c = conn.cursor()
    today = datetime.now().date()

    c.execute("""
        SELECT Loan_id, Due_date, Date_in FROM BOOK_LOANS
        WHERE (Date_in IS NULL AND Due_date < date('now'))
           OR (Date_in IS NOT NULL AND Date_in > Due_date)
    """)

    for loan_id, due_str, date_in_str in c.fetchall():
        due = datetime.strptime(due_str, "%Y-%m-%d").date()
        if date_in_str is None:
            return_date = today
        else:
            return_date = datetime.strptime(date_in_str, "%Y-%m-%d").date()
        days_late = max(0, (return_date - due).days)
        fine = round(days_late * 0.25, 2)

        c.execute("""
            INSERT INTO FINES (Loan_id, Fine_amt) VALUES (?, ?)
            ON CONFLICT(Loan_id) DO UPDATE SET Fine_amt = excluded.Fine_amt
        """, (loan_id, fine))

    conn.commit()
    conn.close()


def pay_fines(card_id: str) -> str:
    """
    Pay fines requirements:
    - Mark all unpaid fines for borrower as Paid
    - No partial payments (all or nothing)
    """
    conn = create_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE FINES 
        SET Paid = 1 
        WHERE Loan_id IN (
            SELECT Loan_id FROM BOOK_LOANS WHERE Card_id = ?
        ) AND Paid = 0
    """, (card_id,))

    count = c.rowcount
    conn.commit()
    conn.close()
    if count == 0:
        return "No unpaid fines found for this card"
    return f"Success: {count} fine(s) paid"