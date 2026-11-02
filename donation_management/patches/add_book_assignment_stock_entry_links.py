from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), update=True)


def get_custom_fields():
	return {
		"Stock Entry": [
			{
				"fieldname": "custom_book_assignment",
				"fieldtype": "Link",
				"label": "Book Assignment",
				"options": "Book Assignment",
				"read_only": 1,
				"insert_after": "purpose",
			},
			{
				"fieldname": "custom_book_stock_action",
				"fieldtype": "Select",
				"label": "Book Stock Action",
				"options": "\nIssued\nReturned\nReissued\nConsumed",
				"read_only": 1,
				"insert_after": "custom_book_assignment",
			},
		]
	}
