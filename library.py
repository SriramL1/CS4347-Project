# library.py
from database import init_db
from operations import search_books

def print_results(results):
    if not results:
        print("\nNo results found.\n")
        return

    # Perfect column headers (exactly like the PDF)
    print(f"\n{'ISBN':<13} {'TITLE':<55} {'AUTHORS':<40} {'STATUS'}")
    print("-" * 140)

    for r in results:
        # Truncate title to 52 chars + "..." if needed
        title = r["title"]
        if len(title) > 55:
            title = title[:52] + "..."

        # Truncate authors if too long
        authors = r["authors"] or "Unknown"
        if len(authors) > 40:
            authors = authors[:37] + "..."

        # Print clean aligned row
        print(f"{r['isbn']:<13} {title:<55} {authors:<40} {r['availability']}")

    print(f"\n{len(results)} result(s) found.\n")
    
if __name__ == "__main__":
    init_db()

    while True:
        print("\n" + "="*55)
        print("     LIBRARY SYSTEM - MILESTONE 2")
        print("="*55)
        print("1. Search Books          ← YOUR PART (100% DONE)")
        print("2. Checkout Book         ← Teammate")
        print("3. Checkin Book          ← Kimberly (Grace) Niemiec (100% DONE)")
        print("4. Add Borrower          ← Teammate")
        print("5. Pay Fines             ← Teammate")
        print("6. Exit")
        choice = input("\nChoice: ").strip()

        if choice == "1":
            q = input("Search (e.g. 'will'): ").strip()
            if q:
                results = search_books(q)
                print_results(results)
            else:
                print("Enter a search term.")
        elif choice == "3":
            query = input("Enter ISBN, Card ID, or Borrower Name to checkin a book: ").strip()
            if query:
                result = checkin_book(query)
                print(result)
            else:
                print("Enter a search term.")
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("That feature is being implemented by your teammate.")
