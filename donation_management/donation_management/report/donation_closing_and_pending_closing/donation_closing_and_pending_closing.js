frappe.query_reports["Donation Closing and Pending Closing"] = {
	onload(report) {
		remove_report_add_button(report, ["Add Donation Closing", "Add Donation Order"]);
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
