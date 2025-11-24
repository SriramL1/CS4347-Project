# operations.py
import sqlite3
from database import create_connection

def search_books(query: str):
    """
    Returns ALL books where the query appears in ISBN, Title, or ANY Author name
    Case-insensitive substring search (exactly as required)
    """
    conn = create_connection()
    c = conn.cursor()

    pattern = f"%{query.strip()}%"

    sql = """
    SELECT 
        b.Isbn,
        b.Title,
        GROUP_CONCAT(DISTINCT a.Name) AS authors,
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
    GROUP BY b.Isbn, b.Title
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

# Teammates will implement these
def checkout_book(isbn, card_id): return "[Pending] Teammate"
def checkin_book(isbn, card_id): return "[Pending] Teammate"
def add_borrower(ssn, name, address, phone=None): return "[Pending] Teammate"
def pay_fines(card_id): return "[Pending] Teammate"
def refresh_fines(): pass