// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Book Page Adjustment", {
	setup(frm) {
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment.get_coupon_book_serials",
			filters: {
				book: frm.doc.book || "",
			},
		}));
	},

	book(frm) {
		if (!frm.doc.book) {
			frm.set_value("book_serial_no", "");
		}
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.book_page_adjustment.book_page_adjustment.get_coupon_book_serials",
			filters: {
				book: frm.doc.book || "",
			},
		}));
	},

	refresh(frm) {
	},
});
