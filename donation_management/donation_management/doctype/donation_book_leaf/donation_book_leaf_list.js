frappe.listview_settings["Donation Book Leaf"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Pending";
		const colors = {
			Received: "blue",
			Used: "green",
			Pending: "orange",
			Cancelled: "red",
			Destroyed: "red",
			Missing: "red",
			"Returned Unused": "gray",
		};

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
