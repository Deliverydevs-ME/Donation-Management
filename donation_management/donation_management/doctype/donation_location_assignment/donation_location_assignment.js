// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donation Location Assignment", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: {
				status: "Active",
			},
		}));
	},
});
