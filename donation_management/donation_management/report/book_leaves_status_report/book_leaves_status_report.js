frappe.query_reports["Book Leaves Status Report"] = {
	onload(report) {
		remove_report_add_button(report, ["Add Donation Book", "Add Book", "Add Donation Order"]);
	},

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

function remove_report_add_button(report, labels) {
	const clear = () => {
		report.page.clear_primary_action();
		$(report.page.wrapper)
			.find("button, a")
			.filter(function () {
				const text = ($(this).text() || "").trim();
				return labels.some((label) => text === __(label) || text.includes(__(label)));
			})
			.remove();
	};

	clear();
	setTimeout(clear, 300);
	setTimeout(clear, 1000);
}
