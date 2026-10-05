frappe.ui.form.on("Donation Book Leaf", {
	setup(frm) {
		frm.set_query("donation_order", () => ({
			query: "donation_management.donation_management.doctype.donation_book_leaf.donation_book_leaf.get_donor_donation_orders",
			filters: {
				donor: frm.doc.donor || "",
				book: frm.doc.book || "",
				book_serial_no: frm.doc.book_serial_no || "",
				receipt_number: frm.doc.receipt_number || "",
			},
		}));

		frm.set_query("journal_entry", () => ({
			query: "donation_management.donation_management.doctype.donation_book_leaf.donation_book_leaf.get_donor_journal_entries",
			filters: {
				donor: frm.doc.donor || "",
			},
		}));
	},

	donor(frm) {
		if (!frm.doc.donor) {
			clear_donor_derived_fields(frm);
		}
		if (frm.__setting_from_donation_order) {
			return;
		}

		if (frm.doc.journal_entry) {
			frm.set_value("journal_entry", "");
		}
		if (frm.doc.donation_order) {
			frm.set_value("donation_order", "");
		}
	},

	donation_order(frm) {
		if (!frm.doc.donation_order) {
			clear_donor_derived_fields(frm);
			frm.set_value("payment_mode", "");
			frm.set_value("manual_receipt_date", "");
			frm.set_value("journal_entry", "");
			frm.set_value("accounting_status", "");
			frm.set_value("amount", 0);
			return;
		}

		frappe.db
			.get_value("Donation Order", frm.doc.donation_order, [
				"donor_name",
				"mode_of_payment",
				"manual_receipt_date",
				"journal_entry",
				"accounting_status",
				"donation_amount",
			])
			.then((response) => {
				const order = response.message || {};
				frm.__setting_from_donation_order = true;
				frm.set_value("donor", order.donor_name || "");
				frm.set_value("payment_mode", order.mode_of_payment || "");
				frm.set_value("manual_receipt_date", order.manual_receipt_date || "");
				frm.set_value("journal_entry", order.journal_entry || "");
				frm.set_value("accounting_status", order.accounting_status || "");
				frm.set_value("amount", order.donation_amount || 0);
				frm.__setting_from_donation_order = false;
			});
	},
});

function clear_donor_derived_fields(frm) {
	frm.set_value("donor", "");
	frm.set_value("payment_mode", "");
	frm.set_value("manual_receipt_date", "");
	frm.set_value("journal_entry", "");
	frm.set_value("accounting_status", "");
	frm.set_value("amount", 0);
}
