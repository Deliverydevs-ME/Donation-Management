frappe.listview_settings["Donation Book Collection"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Draft";
		const colors = { Draft: "gray", Submitted: "blue", Reopened: "orange", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
