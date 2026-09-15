frappe.query_reports["Book Leaves Status Report"] = {
	filters: [
		{
			fieldname: "book",
			label: __("Book"),
			fieldtype: "Link",
			options: "Book",
		},
		{
			fieldname: "book_serial_no",
			label: __("Book Serial No"),
			fieldtype: "Link",
			options: "Serial No",
		},
		{
			fieldname: "status",
			label: __("Leaf Status"),
			fieldtype: "Select",
			options: "\nReceived\nUsed\nPending\nCancelled\nDestroyed\nMissing\nReturned Unused",
		},
		{
			fieldname: "leaf_group",
			label: __("View"),
			fieldtype: "Select",
			options: "\nUnused Books\nPartially Utilized Books\nBooks Waiting for Receiving\nRemaining Leaves\nUsed / Cancelled / Destroyed / Pending Leaves",
		},
	],
};
