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

	validate(frm) {
		if (!frm.doc.employee || !frm.doc.start_date) {
			return;
		}

		return frappe.call({
			method:
				"donation_management.donation_management.doctype.donation_location_assignment.donation_location_assignment.validate_assignment_conflicts",
			args: {
				name: frm.doc.name,
				employee: frm.doc.employee,
				donation_location: frm.doc.donation_location,
				start_date: frm.doc.start_date,
				end_date: frm.doc.end_date,
			},
		});
	},
});
