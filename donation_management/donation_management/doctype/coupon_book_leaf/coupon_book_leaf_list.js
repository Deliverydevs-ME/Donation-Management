frappe.listview_settings["Coupon Book Leaf"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.status || "Pending";
		const colors = { Pending: "orange", Used: "green", Discarded: "red", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `status,=,${status}`];
	},
};
