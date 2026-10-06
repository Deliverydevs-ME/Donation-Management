frappe.listview_settings["Book Assignment"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Draft";
		const colors = { Draft: "gray", Issued: "blue", Returned: "orange", Closed: "green", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
