frappe.listview_settings["Donation Location Assignment"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Draft";
		const colors = {
			Draft: "gray",
			Scheduled: "orange",
			Active: "green",
			Expired: "gray",
			Cancelled: "red",
		};

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
