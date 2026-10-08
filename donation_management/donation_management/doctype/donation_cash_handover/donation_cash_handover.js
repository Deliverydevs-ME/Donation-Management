frappe.ui.form.on("Donation Cash Handover", {
	setup(frm) {
		frm.set_query("donation_closing", () => ({ filters: { docstatus: 1 } }));
	},

	donation_closing(frm) {
		if (!frm.doc.donation_closing) {
			return;
		}

		frappe.db.get_value(
			"Donation Closing",
			frm.doc.donation_closing,
			["company", "cashier", "total_amount"],
			(response) => {
				const closing = response || {};
				frm.set_value("company", closing.company || "");
				frm.set_value("cashier", closing.cashier || "");
				frm.set_value("amount", closing.total_amount || 0);
			}
		);
	},
});
