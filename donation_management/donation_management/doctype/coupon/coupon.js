// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Coupon", {
	setup(frm) {
		frm.set_query("book", () => ({
			query: "donation_management.donation_management.doctype.coupon.coupon.get_available_books",
		}));
		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.coupon.coupon.get_available_coupon_serials",
			filters: { book: frm.doc.book },
		}));
	},

	refresh(frm) {
		if (frm.doc.book) {
			set_coupon_book_details(frm);
		}
	},

	book(frm) {
		set_coupon_book_details(frm);
	},

	number_of_pages(frm) {
		set_coupon_amount(frm);
	},
});

function set_coupon_book_details(frm) {
	if (!frm.doc.book) {
		return;
	}

	frappe.db
		.get_value("Book Assignment", frm.doc.book, [
			"coupon_type",
			"coupon_color",
			"volunteer_name",
			"volunteer_area",
			"warehouse",
			"remaining_pages",
			"coupon_value",
			"status",
			"book_type",
		])
		.then((response) => {
			const book = response.message || {};
			if (
				frm.is_new()
				&& (book.book_type !== "Coupon Book" || book.status !== "Issued" || cint(book.remaining_pages) <= 0)
			) {
				frappe.msgprint({
					title: __("All Pages Used"),
					message: __("Book {0} is not an issued Coupon Book with available pages.", [
						frm.doc.book,
					]),
					indicator: "red",
				});
				frm.set_value("book", "");
				frm.set_value("coupon_color", "");
				frm.set_value("volunteer_name", "");
				frm.set_value("area", "");
				frm.set_value("warehouse", "");
				return;
			}

			frm.set_value("coupon_color", book.coupon_color || "");
			frm.set_value("volunteer_name", book.volunteer_name || "");
			frm.set_value("area", book.volunteer_area || "");
			frm.set_value("warehouse", book.warehouse || "");
			frm.__coupon_value = cint(book.coupon_value);
			if (!cint(frm.doc.number_of_pages)) {
				frm.set_value("number_of_pages", 1);
			}
			set_coupon_amount(frm);
		});
}

function set_coupon_amount(frm) {
	const coupon_value = cint(frm.__coupon_value);
	if (!coupon_value) {
		return;
	}

	frm.set_value("amount", cint(frm.doc.number_of_pages) * coupon_value);
}
