frappe.query_reports["Donation Box Status Report"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nAvailable\nOccupied\nIssued\nPending Receipt\nUnder Collection\nCollected\nReceived\nReturned\nClosed\nCancelled",
		},
		{
			fieldname: "donation_location",
			label: __("Donation Location"),
			fieldtype: "Link",
			options: "Donation Location",
		},
		{
			fieldname: "mohasil",
			label: __("Mohasil"),
			fieldtype: "Link",
			options: "Employee",
		},
	],
};
