frappe.listview_settings["Donation Closing"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Draft";
		const colors = { Draft: "gray", Received: "blue", Deposited: "green", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
