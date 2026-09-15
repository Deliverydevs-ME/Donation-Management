frappe.listview_settings["Donor"] = {
	add_fields: ["customer_name", "donor_phone_number", "primary_address", "territory"],

	onload(listview) {
		listview.page.add_field({
			fieldname: "address",
			label: __("Address"),
			fieldtype: "Data",
			change() {
				const value = this.get_value();
				listview.filter_area.remove("Donor", "primary_address");
				if (value) {
					listview.filter_area.add("Donor", "primary_address", "like", `%${value}%`);
				}
				listview.refresh();
			},
		});
	},
};
