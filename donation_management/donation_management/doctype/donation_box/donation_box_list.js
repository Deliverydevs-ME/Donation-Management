frappe.listview_settings["Donation Box"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Available";
		const colors = {
			Available: "gray",
			Occupied: "orange",
			Issued: "blue",
			"Pending Receipt": "orange",
			"Under Collection": "orange",
			Collected: "purple",
			Received: "green",
			Returned: "gray",
			Closed: "green",
			Cancelled: "red",
		};

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
