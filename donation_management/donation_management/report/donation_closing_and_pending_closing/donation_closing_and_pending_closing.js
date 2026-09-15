frappe.query_reports["Donation Closing and Pending Closing"] = {
	onload(report) {
		report.page.clear_primary_action();
		setTimeout(() => report.page.clear_primary_action(), 300);
	},
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nReceived\nDeposited\nCancelled",
		},
		{
			fieldname: "prepared_by",
			label: __("Prepared By"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
