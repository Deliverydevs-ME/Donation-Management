frappe.listview_settings["Donation Order"] = {
	add_fields: [
		"donor_name",
		"donor_phone_number",
		"donor_email",
		"donor_primary_address",
		"accounting_status",
	],

	get_indicator(doc) {
		const status = doc.docstatus === 2 ? "Cancelled" : doc.accounting_status || "Draft";
		const colors = { "Not Posted": "orange", Posted: "green", Cancelled: "red" };

		return [__(status), colors[status] || "gray", `accounting_status,=,${status}`];
	},

	onload(listview) {
		listview.page.add_field({
			fieldname: "donor_address",
			label: __("Donor Address"),
			fieldtype: "Data",
			change() {
				const value = this.get_value();
				listview.filter_area.remove("Donation Order", "donor_primary_address");
				if (value) {
					listview.filter_area.add("Donation Order", "donor_primary_address", "like", `%${value}%`);
				}
				listview.refresh();
			},
		});
	},
};
