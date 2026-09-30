import frappe


def execute():
	for book in frappe.get_all("Book Assignment", fields=["name", "book_serial_no", "book_type"]):
		serial_rows = frappe.get_all(
			"Book Assignment Detail",
			filters={
				"parent": book.name,
				"parenttype": "Book Assignment",
				"parentfield": "assigned_books",
			},
			fields=["book_serial_no"],
			order_by="idx asc",
		)
		serial_numbers = ", ".join(row.book_serial_no for row in serial_rows if row.book_serial_no)
		if not serial_numbers:
			serial_numbers = book.book_serial_no
		frappe.db.set_value(
			"Book Assignment",
			book.name,
			"book_serial_numbers",
			serial_numbers,
			update_modified=False,
		)
