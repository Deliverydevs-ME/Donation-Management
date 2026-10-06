frappe.ui.form.on("Donation Book Collection", {
	setup(frm) {
		frm.set_query("book", () => ({
			query: "donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_donation_book_assignments",
		}));

		frm.set_query("book_serial_no", () => ({
			query: "donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_donation_book_serials",
			filters: {
				book: frm.doc.book || "",
			},
		}));
	},

	book(frm) {
		if (frm.doc.book_serial_no) {
			frm.set_value("book_serial_no", "");
		}
		clear_book_assignment_details(frm);
	},

	book_serial_no(frm) {
		clear_book_assignment_details(frm);
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}

		frm.add_custom_button(__("Fetch Submitted Receipts"), () => {
			if (!frm.doc.book) {
				frappe.msgprint(__("Select a Book Assignment before fetching receipts."));
				return;
			}
			fetch_submitted_receipts(frm);
		}, __("Actions"));
	},
});

function clear_book_assignment_details(frm) {
	if (frm.doc.book_assignment_details && frm.doc.book_assignment_details.length) {
		frm.clear_table("book_assignment_details");
		frm.refresh_field("book_assignment_details");
	}
}

function fetch_submitted_receipts(frm) {
	const selected_book = frm.doc.book;
	const selected_serial = frm.doc.book_serial_no || "";
	frappe.call({
		method: "donation_management.donation_management.doctype.donation_book_collection.donation_book_collection.get_book_assignment_details",
		args: {
			book: selected_book,
			book_serial_no: selected_serial,
		},
		freeze: true,
		callback(response) {
			if (frm.doc.book !== selected_book || (frm.doc.book_serial_no || "") !== selected_serial) {
				return;
			}

			frm.clear_table("book_assignment_details");
			(response.message || []).forEach((row) => frm.add_child("book_assignment_details", row));
			frm.refresh_field("book_assignment_details");
			if (!(response.message || []).length) {
				frappe.msgprint(__("No submitted Donation Book Leaves with submitted Donation Orders were found."));
			}
		},
	});
}
