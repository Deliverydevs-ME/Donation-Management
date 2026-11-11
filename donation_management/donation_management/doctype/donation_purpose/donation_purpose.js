// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donation Purpose", {
	setup(frm) {
		frm.set_query("credit_account", "account_mappings", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn] || {};
			const filters = {
				is_group: 0,
				root_type: "Income",
			};

			if (row.company) {
				filters.company = row.company;
			}

			return { filters };
		});

		frm.set_query("cost_center", "account_mappings", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn] || {};
			const filters = {
				is_group: 0,
			};

			if (row.company) {
				filters.company = row.company;
			}

			return { filters };
		});
	},
});
