frappe.listview_settings["Book Page Adjustment"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Draft";
		const colors = {
			Draft: "gray",
			"Pending Donation Manager": "orange",
			"Pending Finance Manager": "orange",
			Approved: "green",
			Rejected: "red",
			Cancelled: "red",
		};

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
