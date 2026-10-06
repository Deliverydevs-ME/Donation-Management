frappe.listview_settings["Coupon Entry"] = {
	add_fields: ["accounting_status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.accounting_status || "Draft";
		const colors = { "Not Posted": "orange", Posted: "green", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `accounting_status,=,${status}`];
	},
};
