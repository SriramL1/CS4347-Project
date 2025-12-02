# library.py
from database import init_db
from operations import (search_books, checkout_book, checkin_book,
                        add_borrower, pay_fines, refresh_fines)

def print_results(results):
    if not results:
        print("\nNo results found.\n")
        return
    print(f"\n{'ISBN':<15} {'TITLE':<55} {'AUTHORS':<40} {'STATUS'}")
    print("-" * 140)
    for r in results:
        title = r["title"][:52] + "..." if len(r["title"]) > 55 else r["title"]
        authors = r["authors"][:37] + "..." if len(r["authors"]) > 40 else r["authors"]
        print(f"{r['isbn']:<15} {title:<55} {authors:<40} {r['availability']}")
    print(f"\n{len(results)} result(s) found.\n")

if __name__ == "__main__":
    init_db()
    refresh_fines()  # Update fines on start

    while True:
        print("\n" + "="*40)
        print("     LIBRARY SYSTEM - MAIN MENU")
        print("="*40)
        print("1. Search Books")
        print("2. Checkout Book")
        print("3. Checkin Book")
        print("4. Add Borrower")
        print("5. Pay Fines")
        print("6. Exit")
        choice = input("\nEnter choice (1-6): ").strip()

        if choice == "1":
            q = input("Search (e.g. 'will'): ").strip()
            if q:
                print_results(search_books(q))

        elif choice == "2":
            isbn = input("Enter ISBN: ").strip()
            card = input("Enter Card ID: ").strip()
            print("\n" + checkout_book(isbn, card))

        elif choice == "3":
            isbn = input("Enter ISBN: ").strip()
            card = input("Enter Card ID: ").strip()
            print("\n" + checkin_book(isbn, card))

        elif choice == "4":
            print("Add New Borrower:")
            ssn = input("SSN (format: XXX-XX-XXXX): ").strip()
            name = input("Name: ").strip()
            addr = input("Address: ").strip()
            phone = input("Phone(e.g. (123) 456-7890): ").strip()
            print("\n" + add_borrower(ssn, name, addr, phone))

        elif choice == "5":
            card = input("Enter Card ID to pay fines: ").strip()
            print("\n" + pay_fines(card))

        elif choice == "6":
            print("\nThank you! Goodbye.")
            break
        else:
            print("Invalid choice.")