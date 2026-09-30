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
		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return;
		}

		if (frm.doc.status === "Pending Donation Manager" && frm.has_perm("write")) {
			frm.add_custom_button(__("Approve"), () => frm.call("approve_by_donation_manager"));
			frm.add_custom_button(__("Reject"), () => reject_request(frm), __("Actions"));
		}

		if (frm.doc.status === "Pending Finance Manager" && frm.has_perm("write")) {
			frm.add_custom_button(__("Approve"), () => frm.call("approve_by_finance_manager"));
			frm.add_custom_button(__("Reject"), () => reject_request(frm), __("Actions"));
		}
	},
});

function reject_request(frm) {
	frappe.confirm(__("Reject this page adjustment request?"), () => {
		frm.call("reject_request").then(() => {
			frm.reload_doc();
			frappe.show_alert({ message: __("Request rejected"), indicator: "orange" });
		});
	});
}
